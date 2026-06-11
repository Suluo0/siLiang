"""
Topic API - HTTP 接口层

职责：只负责接收请求、参数校验、调用 service、返回响应
不包含任何业务逻辑
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/topic", tags=["topic"])


class ListResponse(BaseModel):
    """Topic 列表响应"""
    total: int
    items: list[dict]


class DetailResponse(BaseModel):
    """Topic 详情响应"""
    id: str
    topic: str
    alias: list[str] | None = None
    domain: str
    category: str | None = None
    tags: list[str] | None = None
    difficulty: int
    mastery_level: int
    core_summary: str | None = None
    core_points: str | None = None
    detailed_explanation: str | None = None
    code_example: str | None = None
    traps: str | None = None
    bonuses: str | None = None
    prerequisites: list[dict] = []
    core_concepts: list[dict] = []
    derivatives: list[dict] = []
    extensions: list[dict] = []
    evaluation_anchors: list[dict] = []
    similar_questions: list[dict] = []
    advanced_questions: list[dict] = []
    references: list[dict] = []


# 路由
router = APIRouter(prefix="/api/v1/topic", tags=["topic"])

# Service 实例（延迟初始化）
@router.get("/list", response_model=ListResponse)
async def list_topics(
    keyword: str = "", tag: str = "", limit: int = 20, offset: int = 0
):
    """查询 Topic 列表，支持 tag 筛选。高频查询缓存 30 秒。"""
    from src.models import Topic
    from src.api.cache import cache
    
    # 无 keyword 无 tag 时走缓存
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
            "id": str(t.id),
            "topic": t.topic,
            "domain": t.domain,
            "category": t.category,
            "difficulty": t.difficulty,
            "mastery_level": t.mastery_level,
            "tags": tags,
            "keywords": kws,
        })
    return items


@router.get("/tags")
async def list_tags():
    """返回所有唯一的标签（缓存 5 分钟）"""
    from src.api.cache import cache
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


@router.post("/{topic_id}/status")
async def set_topic_status(topic_id: str, request: Request = None):
    """标记题目掌握状态: POST {status: mastered|learning}"""
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
        user_id=uid, topic_id=topic_id,
        defaults={"status": status}
    )
    return {"status": uts.status, "topic_id": topic_id}


@router.get("/dashboard/stats")
async def get_dashboard_stats(request: Request = None):
    """Dashboard 统计数据"""
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
        "mastered": mastered,
        "learning": learning,
        "today_target": today_target,
        "preferences_filled": preferences_filled,
        "authenticated": bool(uid),
    }


@router.get("/positions")
async def get_positions():
    """返回所有可选岗位"""
    from src.models.job_position import JobPosition
    positions = await JobPosition.all().order_by("sort_order")
    return {"items": [{"id": p.id, "name": p.name, "category": p.category} for p in positions]}


@router.get("/{topic_id}")
async def get_topic_detail(topic_id: str, request: Request = None):
    """获取 Topic 详情（quota=0 时截断敏感字段）"""
    from src.models import Topic

    exhausted = getattr(getattr(request, "state", None), "quota_exhausted", False) if request else False

    try:
        topic = await Topic.get(id=topic_id)

        data = {
            "id": str(topic.id),
            "topic": topic.topic,
            "alias": topic.alias,
            "domain": topic.domain,
            "category": topic.category,
            "tags": topic.tags,
            "difficulty": topic.difficulty,
            "mastery_level": topic.mastery_level,
            "core_summary": topic.core_summary,
            "core_points": topic.core_points,
            "detailed_explanation": None,
            "code_example": None,
            "traps": None,
            "bonuses": None,
            "prerequisites": [],
            "core_concepts": [],
            "derivatives": [],
            "extensions": [],
            "evaluation_anchors": [],
            "similar_questions": [],
            "advanced_questions": [],
            "references": [],
            "locked": False,
            "locked_sections": [],
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

        # 关联数据（始终返回）
        data["prerequisites"] = [
            {"content": p.content, "sort_order": p.sort_order}
            async for p in topic.prerequisites.all()
        ]
        data["core_concepts"] = [
            {"content": c.content, "sort_order": c.sort_order}
            async for c in topic.core_concepts.all()
        ]
        data["derivatives"] = [
            {"content": d.content, "sort_order": d.sort_order}
            async for d in topic.derivatives.all()
        ]
        data["extensions"] = [
            {"content": e.content, "sort_order": e.sort_order}
            async for e in topic.extensions.all()
        ]
        data["evaluation_anchors"] = [
            {"level": a.level, "content": a.content, "sort_order": a.sort_order}
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


