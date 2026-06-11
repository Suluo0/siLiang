"""
VERIFY 节点 — 路由决策
读取 RECALL 节点的 verdict，仅做路由，不追加校验逻辑。
"""
from src.agent.state import AgentState, AgentStatus, record_transition


async def verify_node(state: AgentState) -> AgentState:
    record_transition(state, AgentStatus.VERIFYING, "开始路由决策")

    verdict = state.get("verdict", "MISS")

    if verdict == "HIT":
        record_transition(state, AgentStatus.VERIFIED_HIT, "RECALL判定HIT, 直接响应")
    else:
        record_transition(state, AgentStatus.VERIFIED_MISS, "RECALL判定MISS, 进入兜底生成")

    return state
