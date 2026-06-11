"""
generate_topic capability —— LLM 兜底生成
"""
import os
import json
from src.tools.llm_client import LLMClient


_SKILL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "skills", "gen_skill.md")


def _load_skill() -> str:
    with open(_SKILL_PATH, "r", encoding="utf-8") as f:
        return f.read()


async def generate_topic(core_concept: str, domain: str, keywords: list[str]) -> dict:
    """
    从零生成完整面试题 JSON。
    返回: {"topic": dict, "prerequisites": list, ...} + _tokens_used
    """
    llm = LLMClient.get_instance()
    skill = _load_skill()

    prompt = f"""请生成关于以下技术概念的完整面试题：

核心概念：{core_concept}
领域：{domain}
关键词：{", ".join(keywords)}

直接输出 JSON，不要有其他文字。"""

    raw = await llm.ainvoke(
        query=prompt, system_prompt=skill,
        temperature=0.7, max_tokens=4096,
        json_mode=False,
    )

    # 清理 markdown 包裹
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]

    return {
        **json.loads(raw),
        "_tokens_used": 3000,
    }
