"""
check_duplicate capability —— 三层去重 (L1精确 + L2余弦 + L3 Agent验证)
"""
from src.models.topic import Topic


async def check_duplicate(concept: str, domain: str = "") -> dict:
    """
    L1: PostgreSQL 精确匹配
    L2: Milvus 余弦相似度 (≥0.75 → 触发 L3)
    L3: Agent 双分数校验 (余弦 + LLM 语义判定)
    """
    # L1: 精确匹配
    exact = await Topic.filter(topic=concept).first()
    if exact:
        return {
            "duplicate": True,
            "matched_topic": {"topic_id": str(exact.id), "name": exact.topic},
            "similarity": 1.0, "method": "exact_pg",
        }

    # L2: Milvus 余弦检索
    try:
        from src.tools.embedding import EmbeddingEncoder
        from src.tools.milvus_client import MilvusClient
        encoder = EmbeddingEncoder.get_instance()
        milvus = MilvusClient.get_instance()
        vec = encoder.encode(concept)
        hits = milvus.search_dense(vec.tolist(), top_k=1)
    except Exception:
        return {"duplicate": False, "matched_topic": None, "similarity": 0.0, "method": "l1_only"}

    if not hits:
        return {"duplicate": False, "matched_topic": None, "similarity": 0.0, "method": "semantic_none"}

    best = hits[0]
    cosine_score = best.get("score", 0.0)

    if cosine_score < 0.55:
        return {"duplicate": False, "matched_topic": None, "similarity": cosine_score, "method": "semantic"}

    if cosine_score >= 0.75:
        return {
            "duplicate": True,
            "matched_topic": {
                "topic_id": best.get("topic_id"), "name": best.get("core_concept"),
                "domain": best.get("domain"),
            },
            "similarity": cosine_score, "method": "semantic",
        }

    # L3: 余弦 0.55~0.75 之间 — 引入 Agent 双分数二次校验
    candidate_name = best.get("core_concept", "") or ""
    candidate_domain = best.get("domain", "") or ""
    if not candidate_name:
        return {"duplicate": False, "matched_topic": None, "similarity": cosine_score, "method": "semantic_no_name"}

    try:
        from src.agentv3.capabilities.verify import verify_match
        vm = await verify_match(
            query_concept=concept, query_domain=domain,
            candidate_concept=candidate_name, candidate_domain=candidate_domain,
        )
        combined = vm.get("combined", cosine_score)
        passed = vm.get("passed", False)
        reasoning = vm.get("reasoning", "")

        if passed and combined >= 0.60:
            return {
                "duplicate": True,
                "matched_topic": {"topic_id": best.get("topic_id"), "name": candidate_name},
                "similarity": combined, "method": "agent_verify",
                "reasoning": reasoning,
            }
        return {
            "duplicate": False, "warning": True,
            "matched_topic": {"topic_id": best.get("topic_id"), "name": candidate_name},
            "similarity": combined, "method": "agent_verify_ok",
            "reasoning": reasoning,
        }
    except Exception:
        # Agent 不可用时回退到余弦判断
        if cosine_score >= 0.65:
            return {
                "duplicate": True,
                "matched_topic": {"topic_id": best.get("topic_id"), "name": candidate_name},
                "similarity": cosine_score, "method": "semantic_fallback",
            }
        return {"duplicate": False, "matched_topic": None, "similarity": cosine_score, "method": "semantic"}
