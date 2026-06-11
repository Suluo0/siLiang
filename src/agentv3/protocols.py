"""
协议定义 —— ToolResult, SlaveResult, ReasoningStep
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal
import time


@dataclass
class ToolResult:
    """每次 tool 调用的统一返回格式"""
    success: bool
    data: Any = None
    error: str | None = None
    meta: dict = field(default_factory=dict)


@dataclass
class FailedCap:
    """Slave 执行失败的单个能力"""
    capability_id: str
    error: str
    retryable: bool = False


@dataclass
class SlaveResult:
    """Slave 执行结果协议"""
    success: bool
    partial: bool = False
    completed: list[str] = field(default_factory=list)     # 成功的 capability_id
    failed: list[FailedCap] = field(default_factory=list)   # 失败的明细
    compensable: bool = False                                # 是否需要异步补偿
    topic_id: str | None = None
    error: str | None = None


@dataclass
class ReasoningStep:
    """Agent 每步推理记录（可观测性）"""
    step: int
    thought: str
    decision: str
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def format_for_trace(self) -> dict:
        return {
            "step": self.step,
            "thought": self.thought,
            "decision": self.decision,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }
