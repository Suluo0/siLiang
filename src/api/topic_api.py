"""
Topic API - HTTP 接口层

职责：只负责接收请求、参数校验、调用 service、返回响应
不包含任何业务逻辑
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.service.topic_service import TopicService

# 请求/响应模型
class GenerateRequest(BaseModel):
    """生成 Topic 请求"""
    user_input: str
    save_response: bool = True
    streaming: bool = False  # 是否使用流式生成


class GenerateStreamRequest(BaseModel):
    """流式生成 Topic 请求"""
    user_input: str


class GenerateResponse(BaseModel):
    """生成 Topic 响应"""
    success: bool
    message: str
    topic_id: str | None = None
    topic_name: str | None = None
    domain: str | None = None
    difficulty: int | None = None
    error_detail: str | None = None


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
_service: TopicService | None = None


def get_service() -> TopicService:
    """获取 Service 实例"""
    global _service
    if _service is None:
        _service = TopicService()
    return _service


@router.get("/list", response_model=ListResponse)
async def list_topics(
    keyword: str = "", tag: str = "", limit: int = 20, offset: int = 0
):
    """查询 Topic 列表，支持 tag 筛选"""
    from src.models import Topic
    
    query = Topic.all()
    if keyword:
        query = query.filter(topic__icontains=keyword)

    if tag:
        # Tag 在 Python 层过滤——拉 800 条再筛
        topics = await query.order_by("-created_at").limit(800).all()
        items = _build_items(topics, tag)
        total = len(items)
    else:
        total = await query.count()
        topics = await query.order_by("-created_at").offset(offset).limit(limit)
        items = _build_items(topics, tag="")
    
    return ListResponse(total=total, items=items)


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


@router.get("/{topic_id}", response_model=DetailResponse)
async def get_topic_detail(topic_id: str):
    """获取 Topic 详情（含关联数据）"""
    from src.models import Topic
    
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
            "detailed_explanation": topic.detailed_explanation,
            "code_example": topic.code_example,
            "traps": topic.traps,
            "bonuses": topic.bonuses,
            "prerequisites": [
                {"content": p.content, "sort_order": p.sort_order}
                async for p in topic.prerequisites.all()
            ],
            "core_concepts": [
                {"content": c.content, "sort_order": c.sort_order}
                async for c in topic.core_concepts.all()
            ],
            "derivatives": [
                {"content": d.content, "sort_order": d.sort_order}
                async for d in topic.derivatives.all()
            ],
            "extensions": [
                {"content": e.content, "sort_order": e.sort_order}
                async for e in topic.extensions.all()
            ],
            "evaluation_anchors": [
                {"level": a.level, "content": a.content, "sort_order": a.sort_order}
                async for a in topic.evaluation_anchors.all()
            ],
            "similar_questions": [
                {"question": q.question, "answer_hint": q.answer_hint, "sort_order": q.sort_order}
                async for q in topic.similar_questions.all()
            ],
            "advanced_questions": [
                {"question": q.question, "answer_hint": q.answer_hint, "sort_order": q.sort_order}
                async for q in topic.advanced_questions.all()
            ],
            "references": [
                {"title": r.title, "url": r.url, "description": r.description, "sort_order": r.sort_order}
                async for r in topic.references.all()
            ],
        }
        
        return data
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Topic 不存在: {str(e)}")


@router.post("/generate", response_model=GenerateResponse)
async def generate_topic(request: GenerateRequest):
    """
    生成 Topic 完整链路
    
    输入问题 -> 语义转换 -> LLM生成 -> 落库
    """
    try:
        service = get_service()
        result = await service.get_topic_flow(request.user_input)
        
        if not result.success:
            return GenerateResponse(
                success=False,
                message="生成失败",
                error_detail=result.error.message if result.error else None,
            )
        
        return GenerateResponse(
            success=True,
            message="Topic 创建成功",
            topic_id=result.data.get("topic_id"),
            topic_name=result.data.get("topic_name"),
            domain=result.data.get("domain"),
            difficulty=result.data.get("difficulty"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from fastapi.responses import StreamingResponse
from src.service.semantic_trans import semantic_convert, SemanticData


@router.post("/generate/stream")
async def generate_topic_stream(request: GenerateStreamRequest):
    """
    流式生成 Topic（Server-Sent Events）
    完整链路：语义转换 -> 落库 -> 流式LLM生成
    """
    async def event_generator():
        # 1. 语义转换
        trans_result = semantic_convert(request.user_input)
        if not trans_result.success:
            yield 'data: {"type": "error", "message": "语义转换失败"}\n\n'
            return

        semantic_data = trans_result.data
        if not isinstance(semantic_data, SemanticData):
            yield 'data: {"type": "error", "message": "语义转换结果格式异常"}\n\n'
            return

        standardized_output = semantic_data.standardized_output

        # 2. 流式生成，同时收集 chunks
        from src.service.topic_llm import TopicLLMService
        topic_llm = TopicLLMService()

        chunks_list = []
        def save_chunk(chunk):
            chunks_list.append(chunk)

        try:
            # 流式获取数据，落库需要完整 JSON
            topic_data = await topic_llm.generate_topic_and_get_chunks(standardized_output, save_chunk)
        except Exception as e:
            yield f'data: {{"type": "error", "message": "生成面试题失败: {str(e)}"}}\n\n'
            return

        # 3. 落库（包括 topic 表和发送向量队列消息）
        from src.service.topic_service import TopicService
        service = TopicService()

        try:
            topic = await service.save_topic(topic_data)
            yield f'data: {{"type": "saved", "topic_id": "{topic.id}", "topic_name": "{topic.topic}"}}\n\n'

            # 发送向量队列消息
            await service.db_service.send_single_to_embedding_queue(topic.topic)
            yield f'data: {{"type": "embedding_queued"}}\n\n'
        except Exception as e:
            yield f'data: {{"type": "error", "message": "落库失败: {str(e)}"}}\n\n'
            return

        # 4. 流式输出已收集的 chunks
        for chunk in chunks_list:
            yield f'data: {{"type": "chunk", "content": "{chunk}"}}\n\n'

        yield 'data: {"type": "done"}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )