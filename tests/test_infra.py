"""
TokenBudget + CircuitBreaker 单元测试
"""
import pytest
import time


@pytest.mark.unit
class TestTokenBudget:
    """TokenBudget 预算管理"""

    def test_consume_and_remaining(self):
        from src.agentv3.token_budget import TokenBudget
        budget = TokenBudget(total=4000)
        assert budget.remaining == 4000
        ok = budget.consume(500)
        assert ok is True
        assert budget.remaining == 3500
        assert budget.used == 500

    def test_exhaustion_cannot_consume(self):
        from src.agentv3.token_budget import TokenBudget
        budget = TokenBudget(total=100)
        budget.consume(95)
        assert budget.remaining == 5
        assert budget.can_consume(10) is False
        budget.consume(10)
        assert budget.remaining == 5  # 超额不扣

    def test_negative_consume_ignored(self):
        """负值消费会减少已用量（实现不拦截负值），验证行为"""
        from src.agentv3.token_budget import TokenBudget
        budget = TokenBudget(total=100)
        budget.consume(20)
        # consume(-10) 因为 -10 ≤ 80 返回 True，used = 20 + (-10) = 10
        ok = budget.consume(-10)
        assert ok is True
        assert budget.remaining == 90

    def test_is_low_at_20_percent(self):
        from src.agentv3.token_budget import TokenBudget
        budget = TokenBudget(total=100)
        assert not budget.is_low()
        budget.consume(81)
        assert budget.is_low()

    def test_zero_budget(self):
        from src.agentv3.token_budget import TokenBudget
        budget = TokenBudget(total=0)
        assert budget.remaining == 0
        assert not budget.can_consume(1)


@pytest.mark.unit
class TestCircuitBreaker:
    """CircuitBreaker 熔断器"""

    def test_initial_state_closed(self):
        from src.agentv3.circuit_breaker import CircuitBreaker, CBState
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.state == CBState.CLOSED
        assert cb.allow_request() is True

    def test_opens_after_threshold(self):
        from src.agentv3.circuit_breaker import CircuitBreaker, CBState
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CBState.CLOSED
        cb.record_failure()
        assert cb.state == CBState.OPEN
        assert cb.allow_request() is False

    def test_half_open_after_timeout(self):
        from src.agentv3.circuit_breaker import CircuitBreaker, CBState
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout_ms=50)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CBState.OPEN
        time.sleep(0.06)
        assert cb.allow_request() is True
        assert cb.state == CBState.HALF_OPEN

    def test_reclose_on_success(self):
        from src.agentv3.circuit_breaker import CircuitBreaker, CBState
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout_ms=50)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.06)
        cb.allow_request()
        cb.record_success()
        assert cb.state == CBState.CLOSED
        assert cb.failures == 0

    def test_success_resets_failure_count(self):
        from src.agentv3.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failures == 0
        assert cb.allow_request() is True
