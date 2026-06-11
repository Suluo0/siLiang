"""
Agent Graph — LangGraph StateGraph 定义
支持 normalize 节点提前终止（TOO_VAGUE / OUT_OF_SCOPE）
"""
from langgraph.graph import StateGraph, END

from src.agent.state import AgentState, AgentStatus, create_initial_state
from src.agent.nodes.normalize import normalize_node
from src.agent.nodes.recall import recall_node
from src.agent.nodes.verify import verify_node
from src.agent.nodes.generate import generate_node
from src.agent.nodes.dual_write import dual_write_node
from src.agent.nodes.respond import respond_node


def decide_after_normalize(state: AgentState) -> str:
    """normalize 后：正常继续 or 提前终止"""
    if state.get("status") == AgentStatus.DONE:
        return "end"
    return "continue"


def decide_after_verify(state: AgentState) -> str:
    """VERIFY 后的条件边决策"""
    return "hit" if state.get("verdict") == "HIT" else "miss"


def build_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("normalize", normalize_node)
    workflow.add_node("recall", recall_node)
    workflow.add_node("verify", verify_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("dual_write", dual_write_node)
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("normalize")

    # normalize → 正常继续 or 提前终止
    workflow.add_conditional_edges(
        "normalize", decide_after_normalize,
        {"continue": "recall", "end": END}
    )

    workflow.add_edge("recall", "verify")
    workflow.add_edge("generate", "dual_write")
    workflow.add_edge("dual_write", "respond")
    workflow.add_edge("respond", END)

    workflow.add_conditional_edges(
        "verify", decide_after_verify,
        {"hit": "respond", "miss": "generate"}
    )

    return workflow.compile()


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = build_graph()
    return _agent


async def run_agent(user_input: str) -> AgentState:
    agent = get_agent()
    initial_state = create_initial_state(user_input)
    result = await agent.ainvoke(initial_state)
    return result
