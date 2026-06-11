"""
check_duplicate capability —— 去重检查 (L1精确 + L2语义)
"""
from src.models.topic import Topic


async def check_duplicate(concept: str, domain: str = "") -> dict:
    """
    L1: PostgreSQL 精确匹配
    L2: Milvus 语义相似度 (cosine >= 0.85 → duplicate)
    """
    # L1: 精确匹配
    exact = await Topic.filter(topic=concept).first()
    if exact:
        return {
            "duplicate": True,
            "matched_topic": {"topic_id": str(exact.id), "name": exact.topic},
            "similarity": 1.0, "method": "exact_pg",
        }

    # L2: Milvus 语义匹配（延迟导入，避免 sentence-transformers 缺失时崩溃）
    try:
        from src.tools.embedding import EmbeddingEncoder
        from src.tools.milvus_client import MilvusClient
        encoder = EmbeddingEncoder.get_instance()
        milvus = MilvusClient.get_instance()
        vec = encoder.encode(concept)
        hits = milvus.search_dense(vec.tolist(), top_k=3)
    except Exception:
        return {"duplicate": False, "matched_topic": None, "similarity": 0.0, "method": "l1_only"}

    if not hits:
        return {"duplicate": False, "matched_topic": None, "similarity": 0.0, "method": "semantic_none"}

    best = hits[0]
    score = best.get("score", 0.0)

    if score >= 0.85:
        return {
            "duplicate": True,
            "matched_topic": {"topic_id": best.get("topic_id"), "name": best.get("core_concept"), "domain": best.get("domain")},
            "similarity": score, "method": "semantic",
        }
    if score >= 0.75:
        return {
            "duplicate": False, "warning": True,
            "matched_topic": {"topic_id": best.get("topic_id"), "name": best.get("core_concept")},
            "similarity": score, "method": "semantic_warn",
        }

    return {"duplicate": False, "matched_topic": None, "similarity": score, "method": "semantic"}
