"""
TokenBudget —— 累计 token 计数器 + 硬上限
"""
from __future__ import annotations


class TokenBudget:
    """追踪每次 LLM 调用消耗的 token，剩余不足时拒绝调用"""

    def __init__(self, total: int):
        self.total = total
        self.used = 0

    @property
    def remaining(self) -> int:
        return self.total - self.used

    def can_consume(self, tokens: int) -> bool:
        return tokens <= self.remaining

    def consume(self, tokens: int) -> bool:
        if not self.can_consume(tokens):
            return False
        self.used += tokens
        return True

    def is_low(self) -> bool:
        """剩余低于 20%"""
        return self.remaining / self.total < 0.2

    def status_text(self) -> str:
        return f"{self.remaining}/{self.total}" + (" ⚠️" if self.is_low() else "")
