"""
NORMALIZE 节点 — 语义归一化
处理 TOO_VAGUE / LOW_CONFIDENCE 门禁
"""
import os
import json
from src.agent.state import AgentState, AgentStatus, record_transition, NormalizedQuery
from src.tools.llm_client import LLMClient


_SKILL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "skills", "normalize_skill.md"
)


def _load_skill() -> str:
    with open(_SKILL_PATH, "r", encoding="utf-8") as f:
        return f.read()


async def normalize_node(state: AgentState) -> AgentState:
    record_transition(state, AgentStatus.NORMALIZING, "开始语义归一化")
    user_input = state["user_input"]

    skill = _load_skill()
    llm = LLMClient.get_instance()

    # ── LLM 调用 ──
    try:
        raw = await llm.ainvoke(
            query=user_input,
            system_prompt=skill,
            temperature=0.1,
            max_tokens=512,
            json_mode=True,
        )
        parsed = json.loads(raw)
        result = NormalizedQuery(
            core_concept=parsed.get("core_concept", user_input.strip()),
            domain=parsed.get("domain", "未知"),
            subdomain=parsed.get("subdomain"),
            keywords=parsed.get("keywords", []),
            language=parsed.get("language", "zh"),
            confidence=float(parsed.get("confidence", 0.0)),
            boundary_check=parsed.get("boundary_check", "IN_SCOPE"),
        )
    except Exception as e:
        result = NormalizedQuery(
            core_concept=user_input.strip(),
            domain="未知",
            keywords=[],
            confidence=0.0,
            boundary_check="IN_SCOPE",
        )
        state["errors"].append({"node": "normalize", "error": str(e)})

    state["normalized"] = result.model_dump()

    # ── 门禁判定 ──
    # 策略：boundary_check 明确标记 > confidence 数值 > keywords 是否为空

    # 1. 明确标记为不可处理 → 直接拒绝
    if result.boundary_check in ("TOO_VAGUE", "OUT_OF_SCOPE", "UNSUPPORTED_DOMAIN", "UNSUPPORTED_INPUT_TYPE"):
        msg_map = {
            "TOO_VAGUE": f"输入概念过于模糊: 「{user_input}」。请提供更具体的技术概念。",
            "OUT_OF_SCOPE": "输入超出能力范围，请提供单个技术概念。",
            "UNSUPPORTED_DOMAIN": "仅支持技术面试题相关问题。",
            "UNSUPPORTED_INPUT_TYPE": "不支持代码调试类请求。",
        }
        state["verdict"] = "MISS"
        state["response"] = {
            "success": False, "source": "rejected",
            "message": msg_map.get(result.boundary_check, f"输入无法处理: {result.boundary_check}"),
            "trace_id": state["trace_id"],
        }
        record_transition(state, AgentStatus.NORMALIZED,
                          f"REJECTED: {result.boundary_check}")
        state["status"] = AgentStatus.DONE
        return state

    # 2. boundary_check=IN_SCOPE 但 confidence 极低 (< 0.3) → 拒绝
    if result.confidence < 0.3:
        state["verdict"] = "MISS"
        state["response"] = {
            "success": False, "source": "rejected",
            "message": f"无法识别输入中的技术概念: 「{user_input}」。请尝试更具体的描述。",
            "trace_id": state["trace_id"],
        }
        record_transition(state, AgentStatus.NORMALIZED,
                          f"LOW_CONFIDENCE({result.confidence:.2f})")
        state["status"] = AgentStatus.DONE
        return state

    # 3. boundary_check=IN_SCOPE 但 keywords 为空 → 拒绝（关键信号）
    if not result.keywords or len(result.keywords) == 0:
        state["verdict"] = "MISS"
        state["response"] = {
            "success": False, "source": "rejected",
            "message": f"未能从输入中提取到关键词: 「{user_input}」。请使用更完整的技术术语。",
            "trace_id": state["trace_id"],
        }
        record_transition(state, AgentStatus.NORMALIZED, "NO_KEYWORDS")
        state["status"] = AgentStatus.DONE
        return state

    # 4. 通过门禁，继续 pipeline
    if result.confidence < 0.7:
        reason = f"低置信度({result.confidence:.2f})"
    else:
        reason = f"confidence={result.confidence:.2f}, concept={result.core_concept}"

    record_transition(state, AgentStatus.NORMALIZED, reason)
    return state
