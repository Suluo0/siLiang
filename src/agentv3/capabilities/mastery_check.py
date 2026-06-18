"""
mastery_check capability —— 五维掌握度评分（无 LLM，纯向量+字符串计算）

维度:
1. keypoint  (0.35) — 向量余弦: encode(user_answer) vs encode(core_summary + core_points)
2. structure (0.15) — LCS比率: expected_points_order vs answer_sentences_order
3. keyword   (0.20) — 命中率: keywords ∩ answer(精确+编辑距离≤2)
4. length    (0.15) — 长度比: answer_len / expected_len
5. coherence (0.15) — 句间余弦: pairwise cos of answer sentences

mastered = total >= 0.60
"""
import numpy as np
import re

_WEIGHTS = {
    "keypoint": 0.35,
    "structure": 0.15,
    "keyword": 0.20,
    "length": 0.15,
    "coherence": 0.15,
}
_MASTERY_THRESHOLD = 0.60


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[。；;.\n]+", text) if s.strip()]


def _lcs_ratio(a: list[str], b: list[str]) -> float:
    """最长公共子序列比率"""
    if not a or not b:
        return 0.0
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            # 简单包含判断（非严格相等，语义接近即可）
            if a[i-1] in b[j-1] or b[j-1] in a[i-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[m][n] / max(m, n)


def _edit_distance(s1: str, s2: str) -> int:
    """Levenshtein 编辑距离"""
    if len(s1) < len(s2):
        return _edit_distance(s2, s1)
    if not s2:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr.append(min(curr[-1] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def _fuzzy_match(kw: str, text: str, max_dist: int = 2) -> bool:
    """编辑距离 ≤ max_dist 且 kw 长度 > max_dist*2 时视为模糊匹配"""
    if len(kw) <= max_dist:
        return False
    # 滑动窗口：提取 text 中与 kw 等长的片段逐个比对
    for i in range(max(0, len(text) - len(kw) + 1)):
        sub = text[i:i+len(kw)]
        if _edit_distance(kw, sub) <= max_dist:
            return True
    return False


def _compute_coherence(sentences: list[str], encoder) -> float:
    """句间余弦均值"""
    if len(sentences) < 2:
        return 1.0
    try:
        embeddings = [encoder.encode(s) for s in sentences]
        cosines = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                from src.utils import cosine
                cosines.append(cosine(embeddings[i], embeddings[j]))
        return float(np.mean(cosines)) if cosines else 1.0
    except Exception:
        return 0.7  # 编码失败时给中等分


async def mastery_check(
    topic_id: str,
    answer_text: str,
    core_summary: str = "",
    core_points: str = "",
    keywords: list[str] | None = None,
    detailed_explanation: str = "",
) -> dict:
    """
    五维掌握度评分——无 LLM。

    返回:
    {
        "scores": {keypoint, structure, keyword, length, coherence},
        "total": float,
        "mastered": bool,
        "feedback": {
            "keyword": "命中 3/5: HashMap,红黑树,链表。缺少: '扰动函数','哈希冲突'",
            "length": "回答长度适中",
            ...
        }
    }
    """
    from src.tools.embedding import EmbeddingEncoder
    encoder = EmbeddingEncoder.get_instance()

    keywords = keywords or []
    feedback = {}

    # ── 1. Keypoint Coverage ──
    expected_text = (core_summary or "") + " " + (core_points or "")
    if expected_text.strip() and answer_text.strip():
        try:
            v_expected = encoder.encode(expected_text)
            v_answer = encoder.encode(answer_text)
            from src.utils import cosine
            score_keypoint = float(cosine(v_expected, v_answer))
        except Exception:
            score_keypoint = 0.5
    else:
        score_keypoint = 0.0
    feedback["keypoint"] = f"核心概念覆盖度: {score_keypoint*100:.0f}%"

    # ── 2. Structural LCS ──
    exp_points = [p.strip() for p in (core_points or "").split("\n") if p.strip()]
    ans_sentences = _split_sentences(answer_text)
    score_structure = _lcs_ratio(exp_points, ans_sentences) if exp_points and ans_sentences else 0.7
    feedback["structure"] = "结构与期望要点匹配度: {:.0%}".format(score_structure)

    # ── 3. Keyword Density ──
    found = []
    missing = []
    for kw in keywords:
        if kw in answer_text:
            found.append(kw)
        elif _fuzzy_match(kw, answer_text):
            found.append(kw)
        else:
            missing.append(kw)
    score_keyword = len(found) / len(keywords) if keywords else 1.0
    if missing:
        feedback["keyword"] = f"命中 {len(found)}/{len(keywords)}: {found[:4]}。缺少: {missing[:4]}"
    else:
        feedback["keyword"] = f"全部 {len(keywords)} 个关键词已覆盖"

    # ── 4. Length Ratio ──
    exp_len = max(len(detailed_explanation or ""), 50)
    ans_len = len(answer_text)
    ratio = ans_len / exp_len
    if ans_len < 20:
        score_length = 0.0
        feedback["length"] = "回答过短，请详细阐述"
    elif ratio < 0.3:
        score_length = ratio * 0.5
        feedback["length"] = "回答偏短，可补充细节"
    elif ratio > 3.0:
        score_length = 0.7
        feedback["length"] = "回答过于冗长，建议精炼"
    else:
        score_length = min(ratio, 1.0)
        feedback["length"] = "回答长度适中"
    score_length = max(0.0, min(score_length, 1.0))

    # ── 5. Semantic Coherence ──
    score_coherence = _compute_coherence(ans_sentences, encoder)
    feedback["coherence"] = "句间逻辑一致性: {:.0%}".format(score_coherence)

    # ── 总分 ──
    scores = {
        "keypoint": round(score_keypoint, 4),
        "structure": round(score_structure, 4),
        "keyword": round(score_keyword, 4),
        "length": round(score_length, 4),
        "coherence": round(score_coherence, 4),
    }
    total = sum(scores[k] * _WEIGHTS[k] for k in _WEIGHTS)
    total = round(total, 4)
    mastered = total >= _MASTERY_THRESHOLD

    return {
        "scores": scores,
        "total": total,
        "mastered": mastered,
        "feedback": feedback,
    }
