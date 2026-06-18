"""
Phase 5: 三层测试体系 + Golden Dataset 回归
"""
import pytest

# ── Layer 1: 数据模型单元测试 ──


class TestCapabilityRegistry:
    def test_register_and_filter(self):
        from src.agentv3.capabilities.register import register_all
        from src.agentv3.registry import CapabilityRegistry

        register_all()

        # 注册的 capability 数量会随业务扩展而变化,断言下限即可
        all_ids = CapabilityRegistry.list_ids()
        assert len(all_ids) >= 8, f"至少 8 个 capability,实际 {len(all_ids)}"
        # 必须包含核心几个
        for required in ("normalize_input", "check_duplicate", "generate_topic"):
            assert required in all_ids, f"缺少必备 capability: {required}"
        assert len(CapabilityRegistry.filter(scope="read")) >= 6
        assert len(CapabilityRegistry.filter(scope="write")) >= 2

    def test_idempotent(self):
        from src.agentv3.capabilities.register import register_all
        from src.agentv3.registry import CapabilityRegistry

        count_before = len(CapabilityRegistry.list_ids())
        register_all()  # 第二次调用应无副作用
        assert len(CapabilityRegistry.list_ids()) == count_before

    def test_freeze_prevents_register(self):
        from src.agentv3.registry import CapabilityRegistry
        from src.agentv3.capability import Capability, CostTier
        from src.agentv3.permissions import Permission

        CapabilityRegistry.freeze()
        with pytest.raises(RuntimeError, match="已冻结"):
            CapabilityRegistry.register(Capability(
                id="test_frozen", name="t", description="d",
                when_relevant="", when_irrelevant="",
                input_schema={}, output_schema={},
                permissions=[Permission.READ], scope="read",
                handler=lambda: None, estimated_cost=CostTier.FREE,
            ))

    def test_get_nonexistent_raises(self):
        from src.agentv3.registry import CapabilityRegistry
        with pytest.raises(KeyError):
            CapabilityRegistry.get("nonexistent")


class TestSlaveRegistry:
    def test_whitelist_enforcement(self):
        from src.agentv3.slave_registry import SlaveCapabilityRegistry

        SlaveCapabilityRegistry.clear()
        SlaveCapabilityRegistry.register("save_to_postgres")
        SlaveCapabilityRegistry.register("save_to_milvus")

        assert SlaveCapabilityRegistry.is_allowed("save_to_postgres")
        assert SlaveCapabilityRegistry.is_allowed("save_to_milvus")
        assert not SlaveCapabilityRegistry.is_allowed("normalize_input")
        assert not SlaveCapabilityRegistry.is_allowed("delete_topic")


class TestTokenBudget:
    def test_consume_and_remain(self):
        from src.agentv3.token_budget import TokenBudget
        b = TokenBudget(100)
        assert b.remaining == 100
        assert b.consume(30)
        assert b.remaining == 70
        assert not b.consume(100)

    def test_low_warning(self):
        from src.agentv3.token_budget import TokenBudget
        b = TokenBudget(100)
        b.consume(90)
        assert b.is_low()


class TestCircuitBreaker:
    def test_opens_after_threshold(self):
        from src.agentv3.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            assert cb.allow_request()
            cb.record_failure()
        assert not cb.allow_request()

    def test_half_open_allows_one(self):
        from src.agentv3.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout_ms=0)
        cb.record_failure()
        cb.record_failure()
        # recovery_timeout=0 → 立即进入 half_open → allow
        assert cb.allow_request()
        cb.record_success()
        # 成功后回到 closed
        assert cb.allow_request()


class TestSlaveSession:
    def test_rejects_read_capability(self):
        from src.agentv3.capabilities.register import register_all
        from src.agentv3.slave_registry import SlaveCapabilityRegistry
        from src.agentv3.registry import CapabilityRegistry
        from src.agentv3.slave import SlaveSession, SlavePermissionError

        register_all()
        SlaveCapabilityRegistry.clear()
        SlaveCapabilityRegistry.register("normalize_input")

        normalize = CapabilityRegistry.get("normalize_input")
        with pytest.raises(SlavePermissionError, match="不是写能力"):
            SlaveSession(grants=[normalize])

    def test_rejects_non_whitelist(self):
        from src.agentv3.capabilities.register import register_all
        from src.agentv3.slave_registry import SlaveCapabilityRegistry
        from src.agentv3.registry import CapabilityRegistry
        from src.agentv3.slave import SlaveSession, SlavePermissionError

        register_all()
        SlaveCapabilityRegistry.clear()

        save_pg = CapabilityRegistry.get("save_to_postgres")
        with pytest.raises(SlavePermissionError, match="不在 Slave 白名单"):
            SlaveSession(grants=[save_pg])


class TestCapabilityModel:
    def test_format_for_prompt(self):
        from src.agentv3.capability import Capability, CostTier
        from src.agentv3.permissions import Permission

        cap = Capability(
            id="test", name="测试", description="用于测试",
            when_relevant="需要测试时", when_irrelevant="不需要时",
            input_schema={}, output_schema={},
            permissions=[Permission.READ],
            scope="read", handler=lambda: None,
            depends_on=["other"], estimated_cost=CostTier.CHEAP,
        )
        text = cap.format_for_prompt()
        assert "test" in text
        assert "用于测试" in text

    def test_requires_all_fields(self):
        from src.agentv3.capability import Capability, CostTier
        from src.agentv3.permissions import Permission

        cap = Capability(
            id="full", name="全字段", description="d",
            when_relevant="r", when_irrelevant="i",
            input_schema={"a": "int"}, output_schema={"b": "str"},
            permissions=[Permission.READ, Permission.LLM_INVOKE],
            scope="read", handler=lambda x: x,
            precondition=lambda s, **kw: True,
            depends_on=["a", "b"],
            requires_prerequisite=["c"],
            estimated_cost=CostTier.EXPENSIVE,
            estimated_latency_ms=5000,
            fallback="降级说明",
        )
        assert cap.id == "full"
        assert cap.scope == "read"
        assert cap.fallback == "降级说明"


# ── Layer 2: ToolExecutor 保护层测试 ──


class TestToolExecutor:
    @pytest.mark.asyncio
    async def test_precondition_blocks(self):
        from src.agentv3.executor import ToolExecutor
        from src.agentv3.capability import Capability, CostTier
        from src.agentv3.permissions import Permission

        cap = Capability(
            id="blocked", name="b", description="d",
            when_relevant="", when_irrelevant="",
            input_schema={}, output_schema={},
            permissions=[Permission.READ], scope="read",
            handler=lambda: "ok",
            precondition=lambda s, **kw: False,
            estimated_cost=CostTier.FREE,
        )
        exec_ = ToolExecutor(cap)
        result = await exec_.execute({})
        assert not result.success
        assert "前置条件" in result.error

    @pytest.mark.asyncio
    async def test_timeout_triggered(self):
        import asyncio
        from src.agentv3.executor import ToolExecutor
        from src.agentv3.capability import Capability, CostTier
        from src.agentv3.permissions import Permission

        async def slow():
            await asyncio.sleep(5)
            return "ok"

        cap = Capability(
            id="slow", name="s", description="d",
            when_relevant="", when_irrelevant="",
            input_schema={}, output_schema={},
            permissions=[Permission.READ], scope="read",
            handler=slow, estimated_cost=CostTier.FREE,
        )
        exec_ = ToolExecutor(cap, timeout_ms=100)
        result = await exec_.execute({})
        assert not result.success
        assert "超时" in result.error


# ── Layer 3: Golden Dataset 回归测试 ──
#  ⚠️ 此层依赖真实 LLM + Milvus,默认 e2e+slow 标记跳过

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """模块级 fixture - app 只导入一次"""
    from src.main import app
    with TestClient(app) as c:
        yield c


GOLDEN_DATASET = [
    ("HashMap底层实现", "success"),
    ("MySQL事务", "rejected"),
    ("今天天气怎么样", "rejected"),
    ("CAP定理", "success"),
    ("a", "rejected"),
]


class TestGoldenDataset:
    @pytest.mark.parametrize("user_input,expected", GOLDEN_DATASET)
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_regression(self, client, user_input, expected):
        response = client.post("/api/v2/topic/generate", json={"user_input": user_input})

        if response.status_code == 422:
            assert expected == "rejected"
            return

        data = response.json()
        if expected == "rejected":
            assert data.get("success") is False or data.get("source") == "rejected"
        elif expected == "success":
            assert data.get("success") is True
            assert data.get("topic_name") is not None
