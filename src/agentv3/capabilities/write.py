"""
write capabilities —— Slave Session 专用
save_to_postgres / save_to_milvus
"""
import uuid
from src.models.topic import Topic
from src.tools.embedding import EmbeddingEncoder
from src.tools.milvus_client import MilvusClient
from tortoise.transactions import in_transaction


async def save_to_postgres(topic_data: dict) -> dict:
    """
    Slave 专用：写入 PostgreSQL。在事务中执行。
    返回: {"topic_id": str, "topic_name": str, "created": bool}
    """
    topic_info = topic_data.get("topic", {})
    topic_name = topic_info.get("topic", "").strip()
    if not topic_name:
        return {"topic_id": None, "topic_name": "", "created": False, "error": "topic name 为空"}

    async with in_transaction():
        existing = await Topic.filter(topic=topic_name).first()
        if existing:
            return {"topic_id": str(existing.id), "topic_name": topic_name, "created": False}

        tid = str(uuid.uuid4())
        await Topic.create(
            id=tid,
            topic=topic_name,
            alias=topic_info.get("alias"),
            domain=topic_info.get("domain", "编程基础"),
            category=topic_info.get("category"),
            tags=topic_info.get("tags"),
            difficulty=topic_info.get("difficulty", 3),
            mastery_level=topic_info.get("mastery_level", 0),
            review_count=topic_info.get("review_count", 0),
            keywords=topic_info.get("keywords"),
            core_summary=topic_info.get("core_summary"),
            core_points=topic_info.get("core_points"),
            detailed_explanation=topic_info.get("detailed_explanation"),
            code_example=topic_info.get("code_example"),
        )

    return {"topic_id": tid, "topic_name": topic_name, "created": True}


async def save_to_milvus(
    topic_id: str, core_concept: str, domain: str, keywords: str, difficulty: int = 3
) -> dict:
    """
    Slave 专用：写入 Milvus。失败不阻塞。
    返回: {"success": bool, "milvus_id": int | None, "compensable": bool}
    """
    try:
        encoder = EmbeddingEncoder.get_instance()
        vector = encoder.encode(core_concept)
        milvus = MilvusClient.get_instance()
        milvus.insert(
            topic_id=topic_id,
            core_concept=core_concept,
            embedding=vector.tolist(),
            domain=domain,
            keywords=keywords,
            difficulty=difficulty,
        )
        return {"success": True, "compensable": False}
    except Exception as e:
        return {"success": False, "compensable": True, "error": str(e)}
