"""
GENERATE 节点 — Gen_skill 兜底生成
当召回失败时，调用 LLM 从零生成完整面试题 JSON。
"""
import os
import json
from src.agent.state import AgentState, AgentStatus, record_transition
from src.tools.llm_client import LLMClient


_SKILL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "skills", "gen_skill.md")


def _load_skill() -> str:
    with open(_SKILL_PATH, "r", encoding="utf-8") as f:
        return f.read()


async def generate_node(state: AgentState) -> AgentState:
    record_transition(state, AgentStatus.GENERATING, "开始 Gen_skill 兜底生成")

    normalized = state.get("normalized", {})
    core_concept = normalized.get("core_concept", state["user_input"])
    domain = normalized.get("domain", "编程基础")
    keywords = normalized.get("keywords", [])

    skill = _load_skill()
    prompt = f"""请根据以下信息生成完整的面试题数据：

核心概念：{core_concept}
所属领域：{domain}
关键词：{", ".join(keywords)}

直接输出 JSON 结果，不要有任何其他文字。"""

    llm = LLMClient.get_instance()

    try:
        response = await llm.ainvoke(
            query=prompt,
            system_prompt=skill,
            temperature=0.7,
            max_tokens=4096,
            json_mode=False,  # gen_skill 输出就是 JSON
        )
        # 清理可能的 markdown 包裹
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[-1]
            response = response.rsplit("```", 1)[0]
        topic_data = json.loads(response)
    except Exception as e:
        state["errors"].append({"node": "generate", "error": str(e)})
        record_transition(state, AgentStatus.ERROR, f"Gen_skill 生成失败: {e}")
        state["status"] = AgentStatus.ERROR
        return state

    state["generated_topic"] = topic_data
    record_transition(state, AgentStatus.GENERATED, f"topic={topic_data.get('topic', {}).get('topic', 'unknown')}")
    return state
