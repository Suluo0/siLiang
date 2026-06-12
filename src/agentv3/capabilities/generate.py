"""
generate_topic capability —— LLM 兜底生成
两阶段：内容生成 → 拓扑分析
"""
import os
import json
from src.tools.llm_client import LLMClient
from src.utils import clean_json, load_skill

_SKILL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "skills")

_CONTENT_SKILL_PATH = os.path.join(_SKILL_DIR, "gen_topic_content.md")
_TOPOLOGY_SKILL_PATH = os.path.join(_SKILL_DIR, "gen_topic_topology.md")


def _make_topology_input(topic_data: dict, keywords: list[str]) -> str:
    """从阶段一的结果中提取摘要，作为拓扑分析的输入"""
    t = topic_data.get("topic", {})
    summary = f"""题目：{t.get("topic", "")}
领域：{t.get("domain", "")}
技术域：{t.get("tech_domain", t.get("category", ""))}
关键词：{", ".join(keywords) if keywords else t.get("keywords", [])}

内容摘要：
- 一句话概述：{t.get("one_liner", "")}
- 核心要点：{t.get("core_points", "")}
- 正文前200字：{t.get("detailed_explanation", "")[:200]}

请根据以上信息，分析该题目的知识点拓扑关系。直接输出 JSON，不要有任何其他文字。"""
    return summary


async def generate_topic(core_concept: str, domain: str, keywords: list[str]) -> dict:
    """
    两阶段生成完整面试题：
    阶段一：生成题目内容（gen_topic_content.md）
    阶段二：根据内容分析知识点拓扑（gen_topic_topology.md）
    返回: {"topic": dict, "knowledge_points": list, ...} + _tokens_used
    """
    llm = LLMClient.get_instance()

    # ── 阶段一：生成题目内容 ──
    content_skill = load_skill(_CONTENT_SKILL_PATH)
    content_prompt = f"""请生成关于以下技术概念的完整面试题：

核心概念：{core_concept}
领域：{domain}
关键词：{", ".join(keywords)}

直接输出 JSON，不要有其他文字。"""

    raw_content = await llm.ainvoke(
        query=content_prompt, system_prompt=content_skill,
        temperature=0.7, max_tokens=4096,
        json_mode=True,
    )
    topic_data = json.loads(clean_json(raw_content))

    # ── 阶段二：分析知识点拓扑 ──
    topology_skill = load_skill(_TOPOLOGY_SKILL_PATH)
    topology_prompt = _make_topology_input(topic_data, keywords)

    raw_topology = await llm.ainvoke(
        query=topology_prompt, system_prompt=topology_skill,
        temperature=0.3, max_tokens=2048,
        json_mode=True,
    )
    topology_data = json.loads(clean_json(raw_topology))

    return {
        **topic_data,
        **topology_data,
        "_tokens_used": 3000 + 1500,
    }
