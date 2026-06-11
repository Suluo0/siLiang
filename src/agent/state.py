"""
Agent 状态定义
包含状态机状态枚举、业务数据模型、追踪数据模型
"""
import uuid
from enum import StrEnum
from typing import TypedDict, Optional
from datetime import datetime, timezone
from pydantic import BaseModel


# ── 状态机状态枚举 ──

class AgentStatus(StrEnum):
    IDLE = "IDLE"
    NORMALIZING = "NORMALIZING"
    NORMALIZED = "NORMALIZED"
    RECALLING = "RECALLING"
    RECALLED = "RECALLED"
    VERIFYING = "VERIFYING"
    VERIFIED_HIT = "VERIFIED_HIT"
    VERIFIED_MISS = "VERIFIED_MISS"
    GENERATING = "GENERATING"
    GENERATED = "GENERATED"
    DUAL_WRITING = "DUAL_WRITING"
    WRITTEN = "WRITTEN"
    RESPONDING = "RESPONDING"
    DONE = "DONE"
    ERROR = "ERROR"


# ── 归一化数据模型 ──

class NormalizedQuery(BaseModel):
    """归一化查询结果"""
    core_concept: str           # 核心技术概念
    domain: str                 # 一级领域
    subdomain: Optional[str] = None  # 二级子领域
    keywords: list[str] = []    # 关键词列表
    language: str = "zh"        # zh / en / mixed
    confidence: float = 0.0     # 归一化置信度 0-1
    boundary_check: str = "IN_SCOPE"  # IN_SCOPE / OUT_OF_SCOPE / UNSUPPORTED_DOMAIN / UNSUPPORTED_INPUT_TYPE


# ── 召回候选数据模型 ──

class RecallCandidate(BaseModel):
    """召回候选（含 5 层防呆的所有中间分数）"""
    topic_id: str
    core_concept: str
    domain: str
    keywords: list[str] = []
    difficulty: int = 3

    # Layer 2: RRF 融合分
    rrf_score: float = 0.0
    from_dense: bool = False
    from_sparse: bool = False

    # Layer 3: 双分数
    score_a: Optional[float] = None         # 向量余弦
    score_b: Optional[float] = None         # NL 语义匹配
    nl_reasoning: str = ""                  # Score B LLM 判别理由

    # 综合分数（经 Layer 4 交叉验证调整后）
    combined_score: float = 0.0

    # 是否通过全部校验
    passed: bool = False
    reject_reason: Optional[str] = None     # 淘汰原因

    # Layer 4: 交叉验证标记
    cross_validation: str = ""              # AGREE / DISAGREE / SINGLE_SOURCE


# ── Gate 判定结果 ──

class GateResult(BaseModel):
    """防呆门禁判定结果"""
    pass_: bool
    reason: str = ""
    skip_to: str = ""  # MISS / ERROR 等跳转目标


# ── 状态转换追踪 ──

class StateTransition(BaseModel):
    from_status: str
    to_status: str
    timestamp: str = ""
    reason: str = ""
    duration_ms: float = 0.0

    def model_post_init(self, __context):
        if not self.timestamp:
            self.timestamp = datetime.now(tz=timezone.utc).isoformat()


# ── AgentState (LangGraph TypedDict) ──

class AgentState(TypedDict, total=False):
    """LangGraph 状态图的状态对象"""
    # 业务数据
    trace_id: str
    status: str
    user_input: str
    normalized: Optional[dict]      # NormalizedQuery 序列化为 dict
    recall_results: list[dict]      # list[RecallCandidate] 序列化
    verdict: str                    # HIT / MISS
    best_match: Optional[dict]      # RecallCandidate 序列化
    generated_topic: Optional[dict]
    topic_id: Optional[str]

    # RECALL 防呆追踪
    trace_detail: list[dict]        # [{layer: 0, result: ...}, ...]

    # 追踪数据
    state_history: list[dict]       # list[StateTransition]
    node_timings: dict[str, float]  # {node_name: duration_ms}
    errors: list[dict]

    # 最终响应
    response: Optional[dict]


# ── 工厂函数 ──

def create_initial_state(user_input: str) -> AgentState:
    """创建初始 AgentState"""
    return AgentState(
        trace_id=str(uuid.uuid4()),
        status=AgentStatus.IDLE,
        user_input=user_input,
        normalized=None,
        recall_results=[],
        verdict="",
        best_match=None,
        generated_topic=None,
        topic_id=None,
        trace_detail=[],
        state_history=[],
        node_timings={},
        errors=[],
        response=None,
    )


def record_transition(state: AgentState, to_status: str, reason: str = ""):
    """记录状态转换"""
    from_status = state.get("status", AgentStatus.IDLE)
    now = datetime.now(tz=timezone.utc)
    last_entry = state["state_history"][-1] if state["state_history"] else None
    last_ts = datetime.fromisoformat(last_entry["timestamp"]) if last_entry else now
    duration_ms = (now - last_ts).total_seconds() * 1000

    state["status"] = to_status
    state["state_history"].append(StateTransition(
        from_status=from_status,
        to_status=to_status,
        reason=reason,
        duration_ms=round(duration_ms, 2),
    ).model_dump())
