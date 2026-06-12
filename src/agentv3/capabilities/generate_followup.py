"""
generate_followup capability — 根据路由生成下一道面试题
"""
import json
import os
from src.tools.llm_client import LLMClient
from src.utils import clean_json, load_skill

_SKILL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "skills")

_SKILL_MAP = {
    "derivative": os.path.join(_SKILL_DIR, "followup_derivative.md"),
    "extension": os.path.join(_SKILL_DIR, "followup_extension.md"),
    "prerequisite": os.path.join(_SKILL_DIR, "followup_prerequisite.md"),
}


async def generate_followup(
    route: str,
    current_topic_name: str,
    current_domain: str,
    current_difficulty: int,
    extracted_context: dict,
    persona_level: int = 3,
) -> dict:
    """
    根据路由策略生成下一道面试题。

    Args:
        route: derivative / extension / prerequisite
        current_topic_name: 当前题目名称
        current_domain: 当前领域
        current_difficulty: 当前题目难度
        extracted_context: extract_context 的输出
        persona_level: 面试官人设技术深度

    Returns:
        {
            "question_text": str,
            "question_type": str,
            "difficulty": int,
            "topic_keywords": list[str],
            "expected_key_points": list[str],
            "rationale": str
        }
    """
    skill_path = _SKILL_MAP.get(route)
    if not skill_path:
        raise ValueError(f"未知的路由类型: {route}")

    llm = LLMClient.get_instance()
    skill = load_skill(skill_path)

    context_summary = json.dumps(extracted_context, ensure_ascii=False, indent=2)

    # 根据路由调整难度
    difficulty_map = {
        "derivative": min(current_difficulty + 1, 5),
        "extension": current_difficulty,
        "prerequisite": max(current_difficulty - 1, 1),
    }
    target_difficulty = difficulty_map.get(route, 3)

    prompt = f"""当前题目：{current_topic_name}
当前领域：{current_domain}
当前难度：{current_difficulty}/5
面试官技术深度：{persona_level}/5

候选人上下文：
{context_summary}

请生成一道难度为 {target_difficulty}/5 的{route}类型追问。
直接输出 JSON，不要有其他文字。"""

    raw = await llm.ainvoke(
        query=prompt,
        system_prompt=skill,
        temperature=0.3,
        max_tokens=512,
        json_mode=True,
    )

    result = json.loads(clean_json(raw))
    result.setdefault("difficulty", target_difficulty)
    result.setdefault("topic_keywords", [])
    result.setdefault("expected_key_points", [])
    result.setdefault("rationale", "")

    return result
