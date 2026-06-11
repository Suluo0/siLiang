"""
CircuitBreaker —— LLM API 熔断器
连续 N 次失败后熔断，60s 后尝试恢复
"""
from __future__ import annotations
import time
from enum import StrEnum


class CBState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    pass


class CircuitBreaker:
    """熔断器 —— 连续 failure_threshold 次失败后打开"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_ms: int = 60_000,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_ms = recovery_timeout_ms
        self.failures: int = 0
        self.state = CBState.CLOSED
        self._last_failure_time: float = 0.0

    def record_success(self):
        if self.state == CBState.HALF_OPEN:
            self.state = CBState.CLOSED
        self.failures = 0

    def record_failure(self):
        self.failures += 1
        self._last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = CBState.OPEN

    def allow_request(self) -> bool:
        if self.state == CBState.CLOSED:
            return True
        if self.state == CBState.OPEN:
            if (time.time() - self._last_failure_time) * 1000 >= self.recovery_timeout_ms:
                self.state = CBState.HALF_OPEN
                return True
            return False
        if self.state == CBState.HALF_OPEN:
            return True
        return True
