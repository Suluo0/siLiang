"""
search_knowledge capability —— 知识库检索
Milvus 向量检索 + 关键词检索
"""
from src.tools.milvus_client import MilvusClient
from src.tools.embedding import EmbeddingEncoder


async def search_knowledge(concept: str, keywords: list[str], top_k: int = 10) -> dict:
    """
    在知识库中检索已有面试题。
    输入: concept - 核心概念, keywords - 关键词列表
    返回: {"candidates": list[dict], "count": int, "source": "milvus"}
    """
    encoder = EmbeddingEncoder.get_instance()
    milvus = MilvusClient.get_instance()

    # Dense 检索
    query_vec = encoder.encode(concept)
    dense_hits = milvus.search_dense(query_vec.tolist(), top_k=top_k)

    # Sparse 检索
    sparse_hits = milvus.search_sparse(keywords, top_k=top_k)

    # RRF 融合
    scores: dict[str, float] = {}
    for rank, hit in enumerate(dense_hits):
        tid = hit.get("topic_id")
        if tid:
            scores[tid] = scores.get(tid, 0) + 1.0 / (rank + 60)
    for rank, hit in enumerate(sparse_hits):
        tid = hit.get("topic_id")
        if tid:
            scores[tid] = scores.get(tid, 0) + 1.0 / (rank + 60)

    candidates = []
    for tid, rrf in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]:
        d = next((h for h in dense_hits if h.get("topic_id") == tid), None)
        s = next((h for h in sparse_hits if h.get("topic_id") == tid), None)
        src = d or s
        if not src:
            continue
        candidates.append({
            "topic_id": tid,
            "core_concept": src.get("core_concept", ""),
            "domain": src.get("domain", ""),
            "keywords": _parse_keywords(src.get("keywords", "")),
            "dense_cosine": d.get("score") if d else None,
            "rrf_score": rrf,
        })

    return {"candidates": candidates, "count": len(candidates), "source": "milvus"}


def _parse_keywords(raw: str) -> list[str]:
    if not raw:
        return []
    return [kw.strip() for kw in raw.replace("，", ",").split(",") if kw.strip()]
