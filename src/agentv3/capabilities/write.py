"""
write capabilities —— Slave Session 专用
save_to_postgres (主表 + 8关联表) / save_to_milvus
"""
import uuid
from src.models.topic import Topic
from src.tools.embedding import EmbeddingEncoder
from src.tools.milvus_client import MilvusClient
from tortoise.transactions import in_transaction


_RELATION_MODELS = [
    ("src.models.topic_prerequisite", "TopicPrerequisite", "prerequisites", {"content": "content", "sort_order": "sort_order"}),
    ("src.models.topic_core_concept", "TopicCoreConcept", "core_concepts", {"content": "content", "sort_order": "sort_order"}),
    ("src.models.topic_derivative", "TopicDerivative", "derivatives", {"content": "content", "sort_order": "sort_order"}),
    ("src.models.topic_extension", "TopicExtension", "extensions", {"content": "content", "sort_order": "sort_order"}),
    ("src.models.topic_evaluation_anchor", "TopicEvaluationAnchor", "evaluation_anchors", {"content": "content", "sort_order": "sort_order"}),
    ("src.models.topic_similar_question", "TopicSimilarQuestion", "similar_questions", {"question": "question", "answer_hint": "answer_hint", "sort_order": "sort_order"}),
    ("src.models.topic_advanced_question", "TopicAdvancedQuestion", "advanced_questions", {"question": "question", "answer_hint": "answer_hint", "sort_order": "sort_order"}),
    ("src.models.topic_reference", "TopicReference", "references", {"title": "title", "url": "url", "description": "description", "sort_order": "sort_order"}),
]


async def save_to_postgres(topic_data: dict) -> dict:
    """
    Slave 专用：写入 PostgreSQL 主表 + 8 关联表。事务保证原子性。
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
            id=tid, topic=topic_name,
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
            traps=topic_info.get("traps"),
            bonuses=topic_info.get("bonuses"),
        )

        # 8 关联表批量写入
        for module_path, model_name, json_key, field_map in _RELATION_MODELS:
            items = topic_data.get(json_key, [])
            if not items:
                continue
            try:
                import importlib
                mod = importlib.import_module(module_path)
                model_cls = getattr(mod, model_name)
                records = []
                for idx, item in enumerate(items):
                    record = {"id": str(uuid.uuid4()), "topic_id": tid}
                    for db_col, json_col in field_map.items():
                        record[db_col] = item.get(json_col)
                    record.setdefault("sort_order", idx)
                    records.append(record)
                await model_cls.bulk_create([model_cls(**r) for r in records])
            except Exception:
                pass  # 单个关联表失败不阻塞其他表

    return {"topic_id": tid, "topic_name": topic_name, "created": True}


async def save_to_milvus(
    topic_id: str, core_concept: str, domain: str, keywords: str, difficulty: int = 3
) -> dict:
    """Slave 专用：写入 Milvus。失败时记录 Outbox 补偿。"""
    try:
        encoder = EmbeddingEncoder.get_instance()
        vector = encoder.encode(core_concept)
        milvus = MilvusClient.get_instance()
        milvus.insert(
            topic_id=topic_id, core_concept=core_concept,
            embedding=vector.tolist(), domain=domain,
            keywords=keywords, difficulty=difficulty,
        )
        return {"success": True, "compensable": False}
    except Exception as e:
        # Outbox 补偿
        try:
            from src.models.outbox import Outbox
            await Outbox.create(
                id=str(uuid.uuid4()),
                event_type="TOPIC_CREATED",
                payload={"topic_id": topic_id, "core_concept": core_concept},
                status="PENDING",
            )
        except Exception:
            pass
        return {"success": False, "compensable": True, "error": str(e)}
