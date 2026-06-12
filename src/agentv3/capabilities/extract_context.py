"""
extract_context capability — 从面试回答中提取结构化上下文
"""
import json
import os
from src.tools.llm_client import LLMClient
from src.utils import clean_json, load_skill

_SKILL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "skills", "extract_context.md")


async def extract_context(
    question_text: str,
    answer_text: str,
    scores: dict,
) -> dict:
    """
    从单轮面试问答中提取结构化上下文。

    Args:
        question_text: 面试问题
        answer_text: 用户回答
        scores: score_answer 返回的评分结果

    Returns:
        {
            "demonstrated_skills": list[str],
            "knowledge_gaps": list[str],
            "communication_level": int,
            "confidence_level": int,
            "key_quotes": list[str],
            "suggested_next_focus": str
        }
    """
    llm = LLMClient.get_instance()
    skill = load_skill(_SKILL_PATH)

    prompt = f"""请从以下面试问答中提取结构化上下文：

【面试题目】
{question_text}

【候选人回答】
{answer_text}

【评分结果】
总分: {scores.get('total', 0):.2f}
准确性: {scores.get('accuracy', 0):.2f}
深度: {scores.get('depth', 0):.2f}
覆盖度: {scores.get('completeness', 0):.2f}
清晰度: {scores.get('clarity', 0):.2f}
实战: {scores.get('practical', 0):.2f}
缺失知识点: {scores.get('key_missing_points', [])}
评分理由: {scores.get('reasoning', '')}

请按照要求输出 JSON。"""

    raw = await llm.ainvoke(
        query=prompt,
        system_prompt=skill,
        temperature=0.1,
        max_tokens=512,
        json_mode=True,
    )
    result = json.loads(clean_json(raw))

    result.setdefault("demonstrated_skills", [])
    result.setdefault("knowledge_gaps", [])
    result.setdefault("communication_level", 3)
    result.setdefault("confidence_level", 3)
    result.setdefault("key_quotes", [])
    result.setdefault("suggested_next_focus", "")

    return result
