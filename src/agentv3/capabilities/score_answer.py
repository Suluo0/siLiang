"""
score_answer capability — 五维评分面试回答
"""
import json
import os
from src.tools.llm_client import LLMClient
from src.utils import clean_json, load_skill

_SCORE_WEIGHTS = {
    "accuracy": 0.30,
    "depth": 0.25,
    "completeness": 0.15,
    "clarity": 0.15,
    "practical": 0.15,
}

_LABEL_THRESHOLDS = [
    (0.80, "优秀"),
    (0.65, "良好"),
    (0.40, "一般"),
    (0.00, "较差"),
]

_SKILL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "skills", "score_answer.md")


def _classify_label(total: float) -> str:
    for threshold, label in _LABEL_THRESHOLDS:
        if total >= threshold:
            return label
    return "较差"


def _keyword_hit_rate(expected_points: list[str], answer: str) -> float:
    """关键词命中率 — 规则校验"""
    if not expected_points:
        return 1.0
    hits = sum(1 for pt in expected_points if pt in answer)
    return hits / len(expected_points)


async def score_answer(
    question_text: str,
    expected_key_points: list[str],
    user_answer: str,
    question_difficulty: int = 3,
    persona_level: int = 3,
) -> dict:
    """
    对用户面试回答进行五维评分。

    Args:
        question_text: 面试问题文本
        expected_key_points: 期望包含的关键知识点列表
        user_answer: 用户的回答文本
        question_difficulty: 题目难度 1-5
        persona_level: 面试官人设技术深度 1-5

    Returns:
        {
            "accuracy": float, "depth": float, "completeness": float,
            "clarity": float, "practical": float, "total": float,
            "reasoning": str, "key_missing_points": list[str],
            "answer_quality_label": str
        }
    """
    llm = LLMClient.get_instance()
    skill = load_skill(_SKILL_PATH)

    prompt = f"""请对以下面试回答进行五维评分：

【面试题目】
{question_text}

【期望包含的关键知识点】
{', '.join(expected_key_points)}

【候选人回答】
{user_answer}

【题目难度】{question_difficulty}/5
【面试官技术深度要求】{persona_level}/5

请按照五维评分体系输出 JSON。"""

    raw = await llm.ainvoke(
        query=prompt,
        system_prompt=skill,
        temperature=0.0,
        max_tokens=512,
        json_mode=True,
    )
    result = json.loads(clean_json(raw))

    rule_hit_rate = _keyword_hit_rate(expected_key_points, user_answer)
    llm_weights = {
        k: result.get(k, 0.0)
        for k in ["accuracy", "depth", "completeness", "clarity", "practical"]
    }
    llm_weights["accuracy"] = llm_weights["accuracy"] * 0.7 + rule_hit_rate * 0.3

    total = sum(llm_weights[k] * _SCORE_WEIGHTS[k] for k in _SCORE_WEIGHTS)

    if question_difficulty >= 4:
        total = min(total * 1.05, 1.0)
    elif question_difficulty <= 2:
        total = total

    result["total"] = round(total, 4)
    for k in _SCORE_WEIGHTS:
        result[k] = round(llm_weights.get(k, result.get(k, 0.0)), 4)
    result["answer_quality_label"] = _classify_label(total)
    result.setdefault("key_missing_points", [])
    result.setdefault("reasoning", "")

    return result
