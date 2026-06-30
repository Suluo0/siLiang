"""
Topic API — 面试题 CRUD + Agent 生成
"""
import json
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator


# ═══════════════════════════════════════════
# Models
# ═══════════════════════════════════════════

class ListResponse(BaseModel):
    total: int
    items: list[dict]


class GenerateRequest(BaseModel):
    user_input: str

    @field_validator("user_input")
    @classmethod
    def validate_input(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 2:
            raise ValueError("输入过短，请提供更具体的技术概念")
        if len(stripped) > 500:
            raise ValueError("输入过长，请精简到 500 字符以内")
        if stripped.isdigit() or all(not c.isalnum() for c in stripped):
            raise ValueError("请输入有效的技术概念，而非数字或符号")
        return stripped


class GenerateResponse(BaseModel):
    success: bool
    source: str | None = None
    topic_id: str | None = None
    topic_name: str | None = None
    domain: str | None = None
    confidence: float | None = None
    trace_id: str | None = None
    message: str | None = None


router = APIRouter(prefix="/api/topic", tags=["topic"])


# ═══════════════════════════════════════════
# CRUD — 查询
# ═══════════════════════════════════════════

@router.get("/list", response_model=ListResponse)
async def list_topics(
    keyword: str = "", tag: str = "", limit: int = 20, offset: int = 0,
    request: Request = None,
):
    from src.models import Topic
    from src.common.cache import cache

    if not keyword and not tag:
        key = f"topic_list_{limit}_{offset}"
        cached = cache.get(key)
        if cached:
            # 缓存只存题目基础数据;掌握状态按当前用户实时注入(避免串用户)
            await _inject_user_status(cached["items"], request)
            return cached

    query = Topic.all()
    if keyword:
        query = query.filter(topic__icontains=keyword)

    if tag:
        topics = await query.order_by("-created_at").limit(800).all()
        items = _build_items(topics, tag)
        total = len(items)
    else:
        total = await query.count()
        topics = await query.order_by("-created_at").offset(offset).limit(limit)
        items = _build_items(topics, tag="")

    result = ListResponse(total=total, items=items)
    if not keyword and not tag:
        # 入缓存的是不含 user_status 的基础数据
        cache.set(key, result.model_dump(), ttl=30)
    # 注入当前用户掌握状态(不进缓存)
    await _inject_user_status(result.items, request)
    return result


async def _inject_user_status(items: list[dict], request: Request = None) -> None:
    """为题目列表批量注入当前用户的掌握状态(user_status: mastered/learning/None)。
    未登录则全部为 None。单次批量查询,无 N+1。原地修改 items。"""
    for it in items:
        it["user_status"] = None
    uid = getattr(getattr(request, "state", None), "user_id", None) if request else None
    if not uid or not items:
        return
    from src.models.user_topic_status import UserTopicStatus
    topic_ids = [it["id"] for it in items]
    rows = await UserTopicStatus.filter(user_id=uid, topic_id__in=topic_ids).values("topic_id", "status")
    status_map = {str(r["topic_id"]): r["status"] for r in rows}
    for it in items:
        it["user_status"] = status_map.get(str(it["id"]))


def _build_items(topics, tag: str = "") -> list[dict]:
    items = []
    for t in topics:
        tags = t.tags if isinstance(t.tags, list) else []
        kws = t.keywords if isinstance(t.keywords, list) else []
        if tag and tag not in tags and tag not in kws:
            continue
        items.append({
            "id": str(t.id), "topic": t.topic, "domain": t.domain,
            "category": t.category, "difficulty": t.difficulty,
            "mastery_level": t.mastery_level,
            "tags": tags, "keywords": kws,
        })
    return items


@router.get("/tags")
async def list_tags():
    from src.common.cache import cache
    cached = cache.get("topic_tags")
    if cached:
        return cached

    from src.models import Topic
    topics = await Topic.all().limit(2000)
    tag_set = set()
    for t in topics:
        tags = t.tags if isinstance(t.tags, list) else []
        tag_set.update(tags)

    def _quality(tag: str) -> bool:
        has_cn = any('\u4e00' <= c <= '\u9fff' for c in tag)
        if has_cn:
            return True
        if len(tag) <= 2:
            return False
        if tag.isupper() and len(tag) <= 4:
            return False
        return True

    result = {"tags": sorted(t for t in tag_set if _quality(t))}
    cache.set("topic_tags", result, ttl=300)
    return result


@router.get("/positions")
async def get_positions():
    from src.models.job_position import JobPosition
    positions = await JobPosition.all().order_by("sort_order")
    return {"items": [{"id": p.id, "name": p.name, "category": p.category} for p in positions]}


@router.get("/{topic_id}")
async def get_topic_detail(topic_id: str, request: Request = None):
    from src.models import Topic

    exhausted = getattr(getattr(request, "state", None), "quota_exhausted", False) if request else False

    try:
        topic = await Topic.get(id=topic_id)

        data = {
            "id": str(topic.id), "topic": topic.topic, "alias": topic.alias,
            "domain": topic.domain, "tech_domain": topic.tech_domain,
            "category": topic.category, "keywords": topic.keywords,
            "tags": topic.tags, "difficulty": topic.difficulty,
            "mastery_level": topic.mastery_level,
            "one_liner": topic.one_liner,
            "core_summary": topic.core_summary, "core_points": topic.core_points,
            "detailed_explanation": topic.detailed_explanation,
            "code_example": topic.code_example,
            "traps": topic.traps, "bonuses": topic.bonuses,
            "prerequisites": [], "core_concepts": [], "derivatives": [],
            "extensions": [], "evaluation_anchors": [],
            "similar_questions": [], "advanced_questions": [], "references": [],
            "locked": False, "locked_sections": [],
        }

        # 关联数据
        data["prerequisites"] = [
            {"content": (await p.knowledge).name if p.knowledge_id else "", "sort_order": p.sort_order}
            async for p in topic.prerequisites.all().prefetch_related("knowledge")
        ]
        data["core_concepts"] = [
            {"content": (await c.knowledge).name if c.knowledge_id else "", "sort_order": c.sort_order}
            async for c in topic.core_concepts.all().prefetch_related("knowledge")
        ]
        data["derivatives"] = [
            {"content": (await d.knowledge).name if d.knowledge_id else "", "sort_order": d.sort_order}
            async for d in topic.derivatives.all().prefetch_related("knowledge")
        ]
        data["extensions"] = [
            {"content": (await e.knowledge).name if e.knowledge_id else "", "sort_order": e.sort_order}
            async for e in topic.extensions.all().prefetch_related("knowledge")
        ]
        data["evaluation_anchors"] = [
            {"level": a.level, "content": a.question, "sort_order": a.sort_order}
            async for a in topic.evaluation_anchors.all()
        ]
        data["similar_questions"] = [
            {"question": q.question, "answer_hint": q.answer_hint, "sort_order": q.sort_order}
            async for q in topic.similar_questions.all()
        ]
        data["advanced_questions"] = [
            {"question": q.question, "answer_hint": q.answer_hint, "sort_order": q.sort_order}
            async for q in topic.advanced_questions.all()
        ]
        data["references"] = [
            {"title": r.title, "url": r.url, "description": r.description, "sort_order": r.sort_order}
            async for r in topic.references.all()
        ]

        if exhausted:
            return _truncate_json_response(data)

        return data
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Topic 不存在: {str(e)}")


def _truncate_json_response(data: dict, max_len: int = 200) -> dict:
    """序列化完整 data 为 JSON，在 max_len 位置硬切割，修复 JSON 闭合。"""
    raw = json.dumps(data, ensure_ascii=False)

    if len(raw) <= max_len:
        data["locked"] = True
        data["locked_sections"] = ["*"]
        return data

    cut = raw[:max_len]
    # 从尾部回退找到安全切割点：在逗号或闭括号处（确保在字符串外）
    for i in range(max_len - 1, max_len // 2, -1):
        ch = raw[i]
        if ch in (',', '}', ']') and (raw[:i].count('"') - raw[:i].count('\\"')) % 2 == 0:
            cut = raw[:i]
            break

    cut_clean = cut.rstrip(' \t\n\r,')
    open_braces = cut_clean.count('{') - cut_clean.count('}')
    open_brackets = cut_clean.count('[') - cut_clean.count(']')
    result_str = cut_clean + ', "locked":true,"locked_sections":["*"]' + '}' * open_braces + ']' * open_brackets

    try:
        return json.loads(result_str)
    except json.JSONDecodeError:
        return {"id": data.get("id",""), "topic": data.get("topic",""),
                "domain": data.get("domain",""), "difficulty": data.get("difficulty",0),
                "tags": data.get("tags",[]), "locked":True, "locked_sections":["*"]}


# ═══════════════════════════════════════════
# CRUD — 写入
# ═══════════════════════════════════════════

@router.post("/{topic_id}/status")
async def set_topic_status(topic_id: str, request: Request = None):
    from src.models import Topic
    from src.models.user_topic_status import UserTopicStatus
    uid = getattr(getattr(request, "state", None), "user_id", None) if request else None
    if not uid:
        raise HTTPException(status_code=401)

    body = await request.json() if request else {}
    status = body.get("status", "learning")
    if status not in ("mastered", "learning"):
        raise HTTPException(status_code=400, detail="状态仅支持 mastered / learning")

    topic = await Topic.get_or_none(id=topic_id)
    if not topic:
        raise HTTPException(status_code=404)

    uts, _ = await UserTopicStatus.update_or_create(
        user_id=uid, topic_id=topic_id, defaults={"status": status}
    )
    return {"status": uts.status, "topic_id": topic_id}


@router.get("/dashboard/stats")
async def get_dashboard_stats(request: Request = None):
    from src.models import Topic
    from src.models.user_topic_status import UserTopicStatus
    uid = getattr(getattr(request, "state", None), "user_id", None) if request else None
    total = await Topic.all().count()
    today_target = 0
    preferences_filled = False
    if uid:
        from src.models.user import User
        user = await User.filter(id=uid).first()
        if user:
            today_target = user.today_target or 0
            preferences_filled = user.preferences_filled
        mastered = await UserTopicStatus.filter(user_id=uid, status="mastered").count()
        learning = await UserTopicStatus.filter(user_id=uid, status="learning").count()
    else:
        mastered = 0; learning = 0
    return {
        "total_topics": total if uid else 0,
        "mastered": mastered, "learning": learning,
        "today_target": today_target, "preferences_filled": preferences_filled,
        "authenticated": bool(uid),
    }


# ═══════════════════════════════════════════
# Agent 生成
# ═══════════════════════════════════════════

@router.post("/generate", response_model=GenerateResponse)
async def generate_topic_via_agent(req: GenerateRequest):
    from src.agentv3.master import MasterSession

    try:
        master = MasterSession()
        master.grant_slave("save_to_postgres", "save_to_milvus")
        result = await master.handle(req.user_input)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent 执行失败: {e}")

    return GenerateResponse(
        success=result.get("success", False),
        source=result.get("source"),
        topic_id=result.get("topic_id"),
        topic_name=result.get("topic_name"),
        domain=result.get("domain"),
        confidence=result.get("confidence"),
        trace_id=result.get("trace_id"),
        message=result.get("message"),
    )


# ═══════════════════════════════════════════
# 掌握度自查（无 LLM）
# ═══════════════════════════════════════════

class MasteryCheckRequest(BaseModel):
    answer: str

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, v: str) -> str:
        if not v or len(v.strip()) < 10:
            raise ValueError("回答不能为空且不少于 10 字")
        return v.strip()


@router.post("/{topic_id}/mastery-check")
async def mastery_check_endpoint(topic_id: str, req: MasteryCheckRequest, request: Request = None):
    from src.models import Topic
    from src.models.mastery_attempt import MasteryAttempt
    from src.models.user_topic_status import UserTopicStatus
    from src.agentv3.capabilities.mastery_check import mastery_check

    topic = await Topic.filter(id=topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="题目不存在")

    uid = getattr(getattr(request, "state", None), "user_id", None) if request else None
    if not uid:
        raise HTTPException(status_code=401, detail="请先登录")

    # 评分
    result = await mastery_check(
        topic_id=topic_id,
        answer_text=req.answer,
        core_summary=topic.core_summary or "",
        core_points=topic.core_points or "",
        keywords=topic.keywords or [],
        detailed_explanation=topic.detailed_explanation or "",
    )

    # 记录评测
    status, _ = await UserTopicStatus.get_or_create(user_id=uid, topic_id=topic_id, defaults={"status": "learning"})
    prev_attempts = status.mastery_attempts or 0
    status.mastery_attempts = prev_attempts + 1
    status.mastery_score = result["total"]

    if result["mastered"]:
        if status.status != "mastered" or not status.mastered_at:
            status.mastered_at = __import__("datetime").datetime.utcnow()
        status.status = "mastered"
    await status.save()

    await MasteryAttempt.create(
        id=str(__import__("uuid").uuid4()),
        user_id=uid, topic_id=topic_id,
        answer_text=req.answer,
        attempt_number=prev_attempts + 1,
        score_keypoint=result["scores"]["keypoint"],
        score_structure=result["scores"]["structure"],
        score_keyword=result["scores"]["keyword"],
        # length / coherence 维度已废弃(三维重构),旧 DB 列保留为 NULL
        score_total=result["total"],
        is_mastered=result["mastered"],
    )

    return {
        "topic_id": topic_id,
        "total": result["total"],
        "mastered": result["mastered"],
        "scores": result["scores"],
        "feedback": result["feedback"],
    }


@router.get("/{topic_id}/attempts")
async def list_mastery_attempts(topic_id: str, request: Request = None):
    """返回当前用户对该题的历史自查记录(五维分+总分+时间),按时间倒序。"""
    from src.models.mastery_attempt import MasteryAttempt
    from src.models.user_topic_status import UserTopicStatus

    uid = getattr(getattr(request, "state", None), "user_id", None) if request else None
    if not uid:
        raise HTTPException(status_code=401, detail="请先登录")

    attempts = await MasteryAttempt.filter(
        user_id=uid, topic_id=topic_id
    ).order_by("-created_at").limit(50).values(
        "id", "attempt_number", "answer_text",
        "score_keypoint", "score_structure", "score_keyword",
        "score_total",
        "is_mastered", "created_at",
    )

    status = await UserTopicStatus.filter(user_id=uid, topic_id=topic_id).first()
    return {
        "topic_id": topic_id,
        "user_status": status.status if status else None,
        "mastery_score": status.mastery_score if status else 0.0,
        "mastery_attempts": status.mastery_attempts if status else 0,
        "attempts": [
            {
                "id": str(a["id"]),
                "attempt_number": a["attempt_number"],
                "answer_text": a["answer_text"],
                "scores": {
                    "keypoint": a["score_keypoint"],
                    "structure": a["score_structure"],
                    "keyword": a["score_keyword"],
                },
                "total": a["score_total"],
                "is_mastered": a["is_mastered"],
                "created_at": a["created_at"].isoformat() if a["created_at"] else None,
            }
            for a in attempts
        ],
    }
