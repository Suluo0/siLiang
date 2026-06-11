"""
RECALL 节点 — 向量召回 + 5 层防呆校验 + 双分数机制
"""
import json
from typing import TYPE_CHECKING
import numpy as np
from src.agent.state import (
    AgentState, AgentStatus, record_transition,
    NormalizedQuery, RecallCandidate, GateResult,
)
from src.tools.llm_client import LLMClient

if TYPE_CHECKING:
    from src.tools.embedding import EmbeddingEncoder
    from src.tools.milvus_client import MilvusClient


# Score B 判定 Prompt 模板
NL_MATCH_SYSTEM_PROMPT = """你是一个面试题匹配判定器。给定：
  - 用户查询: 归一化后的技术概念
  - 候选题目: 系统中已存储的面试题

请判断候选题目是否真正回答了用户查询。注意：
  - 只判断核心概念是否一致，不要求在细节层面的完全相同
  - 同一概念的不同表述视为匹配（例: "HashMap" = "哈希表" = "散列表"）
  - 不同概念即使共享关键词也不匹配（例: "线程池" ≠ "连接池"）
  - 部分重叠概念按重叠程度评分（例: "Java 并发" 与 "Java 线程池" 评 0.5）

返回严格 JSON: {"score": 0.0-1.0, "reasoning": "一句话解释"}"""

NL_MATCH_USER_TMPL = """用户查询: {query_concept}
查询领域: {query_domain}
候选题目: {candidate_concept}
候选领域: {candidate_domain}

请返回 JSON。"""


# ═══════════════════════════════════════════
# Layer 0: 输入门
# ═══════════════════════════════════════════

def input_gate(nc: NormalizedQuery) -> GateResult:
    if not nc.core_concept or not nc.core_concept.strip():
        return GateResult(pass_=False, reason="EMPTY_INPUT", skip_to="MISS")
    if len(nc.core_concept.strip()) < 2:
        return GateResult(pass_=False, reason="TOO_SHORT", skip_to="MISS")
    if nc.confidence < 0.7:
        return GateResult(pass_=False, reason=f"LOW_CONFIDENCE({nc.confidence:.2f})", skip_to="MISS")
    if nc.boundary_check != "IN_SCOPE":
        return GateResult(pass_=False, reason=f"OUT_OF_SCOPE({nc.boundary_check})", skip_to="MISS")
    return GateResult(pass_=True)


# ═══════════════════════════════════════════
# Layer 1: 向量质量门
# ═══════════════════════════════════════════

def embedding_quality_gate(vector: np.ndarray) -> GateResult:
    if np.any(np.isnan(vector)) or np.any(np.isinf(vector)):
        return GateResult(pass_=False, reason="EMBEDDING_NAN_INF", skip_to="ERROR")
    if vector.shape[-1] != 1024:
        return GateResult(pass_=False, reason=f"EMBEDDING_DIM_MISMATCH({vector.shape[-1]})", skip_to="ERROR")
    if np.all(vector == 0) or np.allclose(vector, 0):
        return GateResult(pass_=False, reason="EMBEDDING_ALL_ZERO", skip_to="ERROR")
    self_sim = _cosine(vector, vector)
    if self_sim < 0.9999:
        return GateResult(pass_=False, reason=f"EMBEDDING_SELF_SIM({self_sim:.6f})", skip_to="ERROR")
    return GateResult(pass_=True)


# ═══════════════════════════════════════════
# Layer 2: 混合检索
# ═══════════════════════════════════════════

def hybrid_search(query_vector: np.ndarray, keywords: list[str], milvus):
    # 零向量 → 跳过 Dense 搜索
    if np.allclose(query_vector, 0):
        dense_hits = []
    else:
        dense_hits = milvus.search_dense(query_vector.tolist(), top_k=10)
    sparse_hits = milvus.search_sparse(keywords, top_k=10)

    if not dense_hits and not sparse_hits:
        return [], {"dense_count": 0, "sparse_count": 0}

    scores: dict[str, float] = {}
    for rank, hit in enumerate(dense_hits):
        tid = hit["topic_id"]
        scores[tid] = scores.get(tid, 0) + 1.0 / (rank + 60)
    for rank, hit in enumerate(sparse_hits):
        tid = hit["topic_id"]
        scores[tid] = scores.get(tid, 0) + 1.0 / (rank + 60)

    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:8]

    candidates = []
    for tid, rrf in sorted_items:
        d = next((h for h in dense_hits if h["topic_id"] == tid), None)
        s = next((h for h in sparse_hits if h["topic_id"] == tid), None)
        src = d or s
        if not src:
            continue
        keywords_list = _parse_keywords(src.get("keywords", ""))
        candidates.append(RecallCandidate(
            topic_id=tid,
            core_concept=src.get("core_concept", ""),
            domain=src.get("domain", ""),
            keywords=keywords_list,
            difficulty=src.get("difficulty", 3),
            rrf_score=rrf,
            from_dense=d is not None,
            from_sparse=s is not None,
            dense_cosine=d.get("score") if d else None,
        ))

    return candidates, {"dense_count": len(dense_hits), "sparse_count": len(sparse_hits)}


# ═══════════════════════════════════════════
# Layer 3: 双分数校验
# ═══════════════════════════════════════════

async def dual_scoring(
    nc: NormalizedQuery,
    candidates: list[RecallCandidate],
    embedding: "EmbeddingEncoder",
    llm: LLMClient,
) -> list[RecallCandidate]:
    query_vector = embedding.encode(nc.core_concept)

    for cand in candidates:
        # Score A: 向量余弦
        cand_vec = embedding.encode(cand.core_concept)
        score_a = _cosine(query_vector, cand_vec)
        cand.score_a = float(score_a)

        if score_a < 0.75:
            cand.passed = False
            cand.reject_reason = f"SCORE_A_LOW({score_a:.3f})"
            continue

        # Score B: NL 语义匹配
        try:
            nl_prompt = NL_MATCH_USER_TMPL.format(
                query_concept=nc.core_concept,
                query_domain=nc.domain,
                candidate_concept=cand.core_concept,
                candidate_domain=cand.domain,
            )
            nl_result = await llm.ainvoke(
                query=nl_prompt,
                system_prompt=NL_MATCH_SYSTEM_PROMPT,
                temperature=0.0,
                max_tokens=128,
                json_mode=True,
            )
            parsed = json.loads(nl_result)
            score_b = float(parsed["score"])
        except Exception:
            score_b = 0.0

        cand.score_b = score_b
        cand.nl_reasoning = parsed.get("reasoning", "")

        if score_b >= 0.70:
            cand.passed = True
            cand.combined_score = 0.5 * score_a + 0.5 * score_b
        else:
            cand.passed = False
            cand.reject_reason = f"SCORE_B_LOW({score_b:.3f})"

    return candidates


# ═══════════════════════════════════════════
# Layer 4: 交叉验证门
# ═══════════════════════════════════════════

def cross_validation_gate(candidates: list[RecallCandidate]) -> list[RecallCandidate]:
    passed = [c for c in candidates if c.passed]
    if not passed:
        return candidates

    dense_top = next((c for c in passed if c.from_dense), None)
    sparse_top = next((c for c in passed if c.from_sparse), None)

    if dense_top and sparse_top:
        if dense_top.topic_id == sparse_top.topic_id:
            for c in passed:
                c.combined_score = min(c.combined_score * 1.05, 1.0)
                c.cross_validation = "AGREE"
        else:
            for c in passed:
                c.combined_score *= 0.85
                c.cross_validation = "DISAGREE"
    else:
        for c in passed:
            c.combined_score *= 0.9
            c.cross_validation = "SINGLE_SOURCE"

    return candidates


# ═══════════════════════════════════════════
# Layer 5: 出口质量门
# ═══════════════════════════════════════════

def output_quality_gate(candidates: list[RecallCandidate]) -> tuple[str, RecallCandidate | None]:
    passed = [c for c in candidates if c.passed]
    if not passed:
        return "MISS", None
    best = max(passed, key=lambda c: c.combined_score)
    if best.combined_score < 0.75:
        return "MISS", None
    return "HIT", best


# ═══════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    a_norm = a / (np.linalg.norm(a) + 1e-12)
    b_norm = b / (np.linalg.norm(b) + 1e-12)
    return float(np.dot(a_norm, b_norm))


def _parse_keywords(raw: str) -> list[str]:
    if not raw:
        return []
    return [kw.strip() for kw in raw.replace("，", ",").split(",") if kw.strip()]


# ═══════════════════════════════════════════
# RECALL 节点主入口
# ═══════════════════════════════════════════

async def recall_node(state: AgentState) -> AgentState:
    record_transition(state, AgentStatus.RECALLING, "开始向量召回")
    trace: list[dict] = []

    normalized_dict = state.get("normalized")
    if not normalized_dict:
        state["verdict"] = "MISS"
        state["recall_results"] = []
        record_transition(state, AgentStatus.RECALLED, "归一化结果为空")
        return state

    nc = NormalizedQuery(**normalized_dict)

    # 暂时跳过召回链路：Embedding 模型下载中 + Milvus 中无数据
    trace.append({"layer": "skip", "reason": "recall unavailable (embedding downloading, no seed data)"})
    state["verdict"] = "MISS"
    state["recall_results"] = []
    state["trace_detail"] = trace
    record_transition(state, AgentStatus.RECALLED, "召回降级 MISS")
    return state

