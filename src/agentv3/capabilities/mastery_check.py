"""
mastery_check capability —— 三维掌握度评分（无 LLM，纯向量+字符串计算）

维度（合计 1.0）:
1. keypoint  (0.55) — whitening 减均值后的相对锚点对比:
     s_good = cos(whiten(answer), whiten(expected))
     s_bad  = cos(whiten(answer), whiten(neg_anchor))   # 通用负锚,off-topic
     score  = clip((s_good - s_bad) / MARGIN_MAX, 0, 1)
   绝对余弦不可信(BGE 各向异性,任意中文余弦都在 0.4~0.7),故取"更靠近对还是错"的相对差。
2. keyword   (0.30) — 命中率: keywords ∩ answer(精确 + 编辑距离≤2 模糊)
3. structure (0.15) — LCS 比率: expected_points_order vs answer_sentences_order

反灌水:对 keypoint / keyword 施加乘性 penalty —— 单字符高占比、低字符多样性(如"啊啊啊")时打折。

被删维度(相比旧五维):
- length    : 篇幅非掌握度证据,且反向奖励灌水 —— 删除
- coherence : 不打句号恒返 1.0、测的是话题一致而非逻辑连贯 —— 删除

mastered = total >= 0.60
"""
import re
from collections import Counter

import numpy as np

_WEIGHTS = {
    "keypoint": 0.55,
    "keyword": 0.30,
    "structure": 0.15,
}
_MASTERY_THRESHOLD = 0.60

# keypoint 相对锚点:margin(s_good - s_bad)达到该值即满分。
# whitening 后,扣题好答案 margin 常达 0.6+,浅答/泛泛而谈约 0.3~0.5,跑题趋近 0 或负。
# 设 0.70 让 keypoint 真正分层(过松会导致只要沾边就满分,区分度塌缩到 keyword)。
_KEYPOINT_MARGIN_MAX = 0.70

# 通用负锚:与任何技术面试答案都 off-topic 的中性段落,用作 s_bad 基线(零成本、无外部依赖)
_NEG_ANCHOR_TEXT = (
    "周末的清晨厨房里飘着煎蛋和咖啡的香气，窗外的麻雀停在晾衣绳上，"
    "邻居家的橘猫慵懒地晒着太阳，远处传来洒水车清扫街道的声音。"
)


def _split_sentences(text: str) -> list[str]:
    # 补中文逗号、顿号:避免"通篇逗号不打句号"被切成单句
    return [s.strip() for s in re.split(r"[。；;.\n，,、！!？?]+", text) if s.strip()]


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
    for i in range(max(0, len(text) - len(kw) + 1)):
        sub = text[i:i+len(kw)]
        if _edit_distance(kw, sub) <= max_dist:
            return True
    return False


def _anti_spam_factor(text: str) -> float:
    """
    反灌水乘性因子 ∈ [0,1]。正常中文答案 ≈ 1.0;"啊啊啊"、"aaaaaa"、单字重复等 → 趋近 0。
    依据两个统计量:
      - 最高频字符占比 most_common_ratio(灌水时极高)
      - 字符多样性 unique_ratio = 不同字符数 / 总字符数(灌水时极低)
    """
    t = re.sub(r"\s+", "", text)
    if len(t) < 2:
        return 0.0
    c = Counter(t)
    most_common_ratio = c.most_common(1)[0][1] / len(t)
    unique_ratio = len(c) / len(t)
    factor = 1.0
    # 单字符占比超 25% 起罚,占比越高罚越狠(0.25→1.0, 0.75→0.0)
    if most_common_ratio > 0.25:
        factor *= max(0.0, 1.0 - (most_common_ratio - 0.25) / 0.5)
    # 字符多样性低于 0.3 起罚(正常中文答案通常 > 0.5)
    if unique_ratio < 0.3:
        factor *= max(0.0, unique_ratio / 0.3)
    return max(0.0, min(1.0, factor))


async def mastery_check(
    topic_id: str,
    answer_text: str,
    core_summary: str = "",
    core_points: str = "",
    keywords: list[str] | None = None,
    detailed_explanation: str = "",
) -> dict:
    """
    三维掌握度评分——无 LLM。

    返回:
    {
        "scores": {keypoint, keyword, structure},
        "total": float,
        "mastered": bool,
        "feedback": {keypoint, keyword, structure, anti_spam?}
    }
    """
    from src.tools.embedding import EmbeddingEncoder
    from src.tools.embedding_mean import whiten
    from src.utils import cosine

    encoder = EmbeddingEncoder.get_instance()
    keywords = keywords or []
    feedback = {}

    # 反灌水因子(先算,后面乘到 keypoint / keyword 上）
    spam_factor = _anti_spam_factor(answer_text)

    # ── 1. Keypoint：whitening 减均值 + 相对锚点 ──
    expected_text = (core_summary or "") + " " + (core_points or "")
    if expected_text.strip() and answer_text.strip():
        try:
            v_answer = whiten(np.asarray(encoder.encode(answer_text), dtype=np.float32))
            v_expected = whiten(np.asarray(encoder.encode(expected_text), dtype=np.float32))
            v_neg = whiten(np.asarray(encoder.encode(_NEG_ANCHOR_TEXT), dtype=np.float32))
            s_good = float(cosine(v_answer, v_expected))
            s_bad = float(cosine(v_answer, v_neg))
            margin = s_good - s_bad
            score_keypoint = max(0.0, min(margin / _KEYPOINT_MARGIN_MAX, 1.0))
        except Exception:
            score_keypoint = 0.5
            s_good = s_bad = 0.0
    else:
        score_keypoint = 0.0
        s_good = s_bad = 0.0
    score_keypoint *= spam_factor
    feedback["keypoint"] = f"核心概念覆盖度: {score_keypoint*100:.0f}%"

    # ── 2. Keyword 命中率 ──
    found, missing = [], []
    for kw in keywords:
        if kw in answer_text or _fuzzy_match(kw, answer_text):
            found.append(kw)
        else:
            missing.append(kw)
    score_keyword = (len(found) / len(keywords)) if keywords else 1.0
    score_keyword *= spam_factor
    # keyword 全命中闸门:该题所有关键词都覆盖到 → 直接判过(无论总分多少)。
    # 关键词全提到说明该记的点都记住了,不再卡 keypoint/structure 的加权总分。
    keyword_gate = bool(keywords) and not missing
    if missing:
        feedback["keyword"] = f"命中 {len(found)}/{len(keywords)}: {found[:4]}。缺少: {missing[:4]}"
    else:
        feedback["keyword"] = f"全部 {len(keywords)} 个关键词已覆盖"

    # ── 3. Structural LCS ──
    exp_points = [p.strip() for p in (core_points or "").split("\n") if p.strip()]
    ans_sentences = _split_sentences(answer_text)
    score_structure = _lcs_ratio(exp_points, ans_sentences) if exp_points and ans_sentences else 0.5
    feedback["structure"] = "结构与期望要点匹配度: {:.0%}".format(score_structure)

    if spam_factor < 0.95:
        feedback["anti_spam"] = f"检测到低信息量/重复内容，已对得分打折 (×{spam_factor:.2f})"

    # ── 总分 ──
    scores = {
        "keypoint": round(score_keypoint, 4),
        "keyword": round(score_keyword, 4),
        "structure": round(score_structure, 4),
    }
    total = round(sum(scores[k] * _WEIGHTS[k] for k in _WEIGHTS), 4)
    # 达标 = 加权总分过阈值 或 关键词全命中闸门触发
    mastered = total >= _MASTERY_THRESHOLD or keyword_gate
    if keyword_gate and total < _MASTERY_THRESHOLD:
        feedback["gate"] = "关键词全部覆盖,已直接判定掌握"

    return {
        "scores": scores,
        "total": total,
        "mastered": mastered,
        "feedback": feedback,
    }
