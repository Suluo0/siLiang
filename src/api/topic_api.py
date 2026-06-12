"""
Topic API — 面试题 CRUD + Agent 生成
"""
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
    keyword: str = "", tag: str = "", limit: int = 20, offset: int = 0
):
    from src.models import Topic
    from src.common.cache import cache

    if not keyword and not tag:
        key = f"topic_list_{limit}_{offset}"
        cached = cache.get(key)
        if cached:
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
        cache.set(key, result.model_dump(), ttl=30)
    return result


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
    result = {"tags": sorted(tag_set)}
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
            "detailed_explanation": None, "code_example": None,
            "traps": None, "bonuses": None,
            "prerequisites": [], "core_concepts": [], "derivatives": [],
            "extensions": [], "evaluation_anchors": [],
            "similar_questions": [], "advanced_questions": [], "references": [],
            "locked": False, "locked_sections": [],
        }

        if exhausted:
            data["locked"] = True
            data["locked_sections"] = ["detailed_explanation", "code_example", "traps", "bonuses"]
            expl = topic.detailed_explanation or ""
            data["detailed_explanation"] = expl[:200] if len(expl) > 200 else expl
        else:
            data["detailed_explanation"] = topic.detailed_explanation
            data["code_example"] = topic.code_example
            data["traps"] = topic.traps
            data["bonuses"] = topic.bonuses

        # 关联数据 — join 表真实内容在 knowledge.name / evaluation.question
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

        return data
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Topic 不存在: {str(e)}")


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
