"""
ToolExecutor —— 每个 Capability 调用的运行时保护 + 落库追踪
trace_id / caller 由 contextvars 自动获取，无需外部传入。
"""
from __future__ import annotations
import asyncio, time, uuid

from src.agentv3.capability import Capability
from src.agentv3.protocols import ToolResult
from src.agentv3.token_budget import TokenBudget
from src.agentv3.circuit_breaker import CircuitBreaker, CircuitBreakerError
from src.utils.context import current_trace_id, current_caller


def _sanitize(data, max_length: int = 500, max_items: int = 5):
    forbidden_keys = {"raw_prompt", "system_instructions", "api_key", "password"}
    if isinstance(data, str):
        return data[:max_length] + "..." if len(data) > max_length else data
    if isinstance(data, dict):
        return {k: _sanitize(v) for k, v in data.items() if k not in forbidden_keys}
    if isinstance(data, list):
        return [_sanitize(v) for v in data[:max_items]]
    return data


async def _log_call(trace_id: str, cap_id: str, status: str, duration_ms: int,
                    input_summary: str = None, output_summary: str = None, error: str = None):
    """异步写 PromptCallLog。任何异常静默忽略。"""
    try:
        from src.models.prompt_call_log import PromptCallLog
        await PromptCallLog.create(
            id=str(uuid.uuid4()),
            trace_id=trace_id or "",
            capability_id=cap_id or "",
            status=status or "unknown",
            duration_ms=duration_ms or 0,
            user_prompt=(input_summary or "")[:500],
            output_content=(output_summary or "")[:1000],
            error_message=(error or "")[:500],
            model="deepseek-chat",
        )
    except Exception:
        pass  # 落库失败不影响主流程


class ToolExecutor:
    DEFAULT_TIMEOUT_MS = 30_000

    def __init__(
        self,
        cap: Capability,
        budget: TokenBudget | None = None,
        breaker: CircuitBreaker | None = None,
        timeout_ms: int | None = None,
    ):
        self.cap = cap
        self.trace_id = current_trace_id.get()
        self.caller = current_caller.get()
        self.budget = budget
        self.breaker = breaker
        self.timeout_ms = timeout_ms or self.DEFAULT_TIMEOUT_MS

    async def execute(self, state: dict, **kwargs) -> ToolResult:
        t_start = time.monotonic()

        if self.breaker and not self.breaker.allow_request():
            return ToolResult(success=False, error="LLM API 当前不可用（熔断中）",
                              meta={"circuit_breaker": "open"})

        if self.cap.precondition is not None:
            if not self.cap.precondition(state, **kwargs):
                return ToolResult(success=False, error=f"前置条件不满足: {self.cap.id}",
                                  meta={"reason": "precondition_failed"})

        try:
            if asyncio.iscoroutinefunction(self.cap.handler):
                result = await asyncio.wait_for(
                    self.cap.handler(**kwargs), timeout=self.timeout_ms / 1000)
            else:
                result = self.cap.handler(**kwargs)
        except asyncio.TimeoutError:
            await _log_call(self.trace_id, self.cap.id, "failed",
                            self.timeout_ms, error="超时")
            return ToolResult(success=False, error=f"{self.cap.id} 执行超时 ({self.timeout_ms}ms)")
        except CircuitBreakerError as e:
            return ToolResult(success=False, error=str(e), meta={"circuit_breaker": "tripped"})
        except Exception as e:
            if self.breaker:
                self.breaker.record_failure()
            duration = int((time.monotonic() - t_start) * 1000)
            await _log_call(self.trace_id, self.cap.id, "failed", duration, error=str(e))
            return ToolResult(success=False, error=f"{self.cap.id} 执行异常: {e}")

        result = _sanitize(result)
        tokens = 0
        if isinstance(result, dict):
            tokens = result.pop("_tokens_used", 0)
        if self.budget and tokens:
            self.budget.consume(tokens)
        if self.breaker:
            self.breaker.record_success()

        duration = int((time.monotonic() - t_start) * 1000)
        input_summary = kwargs.get("user_input", str(list(kwargs.values())[:1])) if kwargs else ""
        await _log_call(self.trace_id, self.cap.id, "success", duration,
                        input_summary=str(kwargs)[:300], output_summary=str(result)[:500])

        return ToolResult(success=True, data=result,
                          meta={"tokens_used": tokens,
                                "tokens_remaining": self.budget.remaining if self.budget else None,
                                "budget_warning": "low" if self.budget and self.budget.is_low() else None})
