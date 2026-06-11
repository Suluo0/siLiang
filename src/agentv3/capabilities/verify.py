"""
verify_match capability —— 双分数候选校验
Embedding 余弦 + LLM 语义判定
"""
import json
from src.tools.embedding import EmbeddingEncoder
from src.tools.llm_client import LLMClient


NL_MATCH_PROMPT = """你是一个面试题匹配判定器。
判断候选题目是否真正回答了用户查询。
注意：同一概念的不同表述视为匹配（HashMap=哈希表），不同概念即使共享关键词也不匹配（线程池≠连接池）。
返回 JSON: {"score": 0.0-1.0, "reasoning": "一句话解释"}"""


async def verify_match(
    query_concept: str,
    query_domain: str,
    candidate_concept: str,
    candidate_domain: str,
) -> dict:
    """
    对单个候选进行双分数校验。
    返回: {"score_a": float, "score_b": float, "combined": float, "passed": bool, "reasoning": str}
    """
    encoder = EmbeddingEncoder.get_instance()
    llm = LLMClient.get_instance()

    # Score A: 向量余弦
    query_vec = encoder.encode(query_concept)
    cand_vec = encoder.encode(candidate_concept)
    score_a = _cosine(query_vec, cand_vec)

    if score_a < 0.75:
        return {
            "score_a": score_a, "score_b": None, "combined": score_a,
            "passed": False, "reasoning": f"向量相似度过低 ({score_a:.3f})",
        }

    # Score B: NL 语义匹配
    raw = await llm.ainvoke(
        query=f"用户查询: {query_concept}\n查询领域: {query_domain}\n候选: {candidate_concept}\n候选领域: {candidate_domain}",
        system_prompt=NL_MATCH_PROMPT,
        temperature=0.0, max_tokens=128, json_mode=True,
    )
    parsed = json.loads(raw)
    score_b = float(parsed.get("score", 0))

    combined = 0.5 * score_a + 0.5 * score_b
    return {
        "score_a": score_a, "score_b": score_b, "combined": combined,
        "passed": score_b >= 0.70,
        "reasoning": parsed.get("reasoning", ""),
    }


def _cosine(a, b):
    import numpy as np
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))
