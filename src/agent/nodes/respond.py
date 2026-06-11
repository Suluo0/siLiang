"""
RESPOND 节点 — 响应组装
优先级: generated/recalled > errors
"""
from src.agent.state import AgentState, AgentStatus, record_transition


async def respond_node(state: AgentState) -> AgentState:
    record_transition(state, AgentStatus.RESPONDING, "组装响应")
    verdict = state.get("verdict", "MISS")
    trace_id = state.get("trace_id", "")

    # HIT 路径 — 召回命中
    if verdict == "HIT" and state.get("best_match"):
        best = state["best_match"]
        state["response"] = {
            "success": True, "source": "recall",
            "topic_id": best.get("topic_id"),
            "topic_name": best.get("core_concept"),
            "domain": best.get("domain"),
            "confidence": best.get("combined_score"),
            "trace_id": trace_id,
        }
        record_transition(state, AgentStatus.DONE, "recall HIT")
        return state

    # MISS 路径 — 生成成功
    if state.get("topic_id"):
        gen_topic = state.get("generated_topic", {}).get("topic", {})
        state["response"] = {
            "success": True, "source": "generated",
            "topic_id": state["topic_id"],
            "topic_name": gen_topic.get("topic", ""),
            "domain": gen_topic.get("domain", ""),
            "trace_id": trace_id,
        }
        record_transition(state, AgentStatus.DONE, "generated OK")
        return state

    # 无结果 — 报错
    errors = state.get("errors", [])
    msg = "; ".join([e.get("error", e.get("pg_error", e.get("reason", ""))) for e in errors]) if errors else "未知错误"
    state["response"] = {
        "success": False, "source": "error",
        "message": msg, "trace_id": trace_id,
    }
    record_transition(state, AgentStatus.DONE, f"error: {msg[:80]}")
    return state
