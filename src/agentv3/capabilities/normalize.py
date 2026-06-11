"""
normalize_input capability —— 语义归一化
将用户自由文本结构化为 NormalizedQuery
"""
import os
import json
from src.tools.llm_client import LLMClient


_SKILL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "skills", "normalize_skill.md")


def load_skill() -> str:
    with open(_SKILL_PATH, "r", encoding="utf-8") as f:
        return f.read()


async def normalize_input(user_input: str) -> dict:
    """
    语义归一化：将用户自由文本转化为结构化查询对象。
    输入: user_input - 用户原始文本
    返回: {"core_concept": str, "domain": str, "keywords": list[str], "confidence": float, "boundary_check": str, "_tokens_used": int}
    """
    llm = LLMClient.get_instance()
    skill = load_skill()

    raw = await llm.ainvoke(
        query=user_input,
        system_prompt=skill,
        temperature=0.1,
        max_tokens=512,
        json_mode=True,
    )
    parsed = json.loads(raw)
    return {
        "core_concept": parsed.get("core_concept", ""),
        "domain": parsed.get("domain", ""),
        "subdomain": parsed.get("subdomain"),
        "keywords": parsed.get("keywords", []),
        "language": parsed.get("language", "zh"),
        "confidence": float(parsed.get("confidence", 0.0)),
        "boundary_check": parsed.get("boundary_check", "IN_SCOPE"),
        "_tokens_used": 250,  # 估算
    }
