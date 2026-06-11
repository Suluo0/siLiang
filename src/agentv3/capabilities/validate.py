"""
validate_output capability —— 生成内容质量校验
"""
import json
from src.tools.llm_client import LLMClient


VALIDATE_PROMPT = """你是一个面试题质量校验器。
检查生成的面试题数据是否符合质量标准。
判断标准：
1. 主概念非空，且与用户查询相关
2. domain/category 分类合理
3. core_summary 在 15-100 字之间
4. keywords 至少 2 个
5. 关键技术点 core_points 至少有 2 条
返回 JSON: {"valid": bool, "quality": 0.0-1.0, "issues": ["问题1", "问题2"]}"""


async def validate_output(topic_data: dict, expected_concept: str) -> dict:
    """
    LLM 校验生成内容的质量。
    返回: {"valid": bool, "quality": float, "issues": list[str]}
    """
    llm = LLMClient.get_instance()
    topic_summary = json.dumps(topic_data.get("topic", {}), ensure_ascii=False)[:800]

    raw = await llm.ainvoke(
        query=f"期望概念: {expected_concept}\n生成数据: {topic_summary}",
        system_prompt=VALIDATE_PROMPT,
        temperature=0.0, max_tokens=256, json_mode=True,
    )
    parsed = json.loads(raw)
    return {
        "valid": parsed.get("valid", False),
        "quality": float(parsed.get("quality", 0)),
        "issues": parsed.get("issues", []),
    }
