"""
AgentSession —— 预算管理 + 推理链记录 + 会话生命周期
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field

from src.agentv3.token_budget import TokenBudget


class AgentGuardError(Exception):
    """三类预算任意一项耗尽时抛出"""
    pass


@dataclass
class AgentSession:
    """管理单个请求的会话生命周期"""

    trace_id: str
    user_input: str

    # 预算
    token_budget: TokenBudget
    max_iterations: int = 8
    max_total_time_ms: int = 30_000

    # 运行时状态
    iterations: int = 0
    start_time: float = field(default_factory=time.time)
    reasoning_chain: list[dict] = field(default_factory=list)
    cancelled: bool = False

    def guard(self) -> None:
        """每轮循环前检查。任一预算耗尽抛出 AgentGuardError。"""
        self.iterations += 1

        if self.cancelled:
            raise AgentGuardError("会话已被取消")

        if self.iterations > self.max_iterations:
            raise AgentGuardError(
                f"达到最大迭代次数 ({self.max_iterations})"
            )

        elapsed_ms = (time.time() - self.start_time) * 1000
        if elapsed_ms >= self.max_total_time_ms:
            raise AgentGuardError(
                f"达到时间预算上限 ({self.max_total_time_ms}ms, 已用 {int(elapsed_ms)}ms)"
            )

        if self.token_budget.remaining <= 0:
            raise AgentGuardError(
                f"达到 token 预算上限 ({self.token_budget.total})"
            )

    def record_reasoning(self, thought: str, decision: str, confidence: float = 0.0):
        self.reasoning_chain.append({
            "step": self.iterations,
            "thought": thought,
            "decision": decision,
            "confidence": confidence,
            "timestamp": time.time(),
        })

    @property
    def elapsed_ms(self) -> int:
        return int((time.time() - self.start_time) * 1000)

    def cancel(self):
        self.cancelled = True
