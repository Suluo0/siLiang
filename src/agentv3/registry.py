"""
CapabilityRegistry —— 全局能力注册表 + 统一切面执行入口
启动时注册，freeze 后不可变。
"""
from __future__ import annotations
from src.agentv3.capability import Capability
from src.agentv3.permissions import Permission
from src.agentv3.executor import ToolExecutor
from src.agentv3.protocols import ToolResult
from src.agentv3.circuit_breaker import CircuitBreaker
from src.utils.context import current_budget


class CapabilityExecutionError(Exception):
    """能力执行失败异常"""
    def __init__(self, cap_id: str, error: str):
        self.cap_id = cap_id
        self.error = error
        super().__init__(f"[{cap_id}] {error}")


class CapabilityRegistry:
    """全局能力注册表。启动时注册所有能力，运行时不可变。"""

    _registry: dict[str, Capability] = {}
    _frozen: bool = False
    _breaker_map: dict[str, CircuitBreaker] = {}

    # ── 注册 ──

    @classmethod
    def register(cls, cap: Capability):
        if cls._frozen:
            raise RuntimeError(f"Registry 已冻结，不可注册新能力 (尝试注册: {cap.id})")
        if cap.id in cls._registry:
            raise ValueError(f"能力 ID 重复: {cap.id}")
        cls._registry[cap.id] = cap

    @classmethod
    def freeze(cls):
        cls._frozen = True

    # ── 查询 ──

    @classmethod
    def get(cls, id_: str) -> Capability:
        if id_ not in cls._registry:
            raise KeyError(f"未注册的能力: {id_}")
        return cls._registry[id_]

    @classmethod
    def filter(
        cls,
        *,
        scope: str | None = None,
        permissions: list[Permission] | None = None,
    ) -> list[Capability]:
        result = []
        for cap in cls._registry.values():
            if scope and cap.scope != scope:
                continue
            if permissions:
                cap_perm_set = set(cap.permissions)
                if not any(p in cap_perm_set for p in permissions):
                    continue
            result.append(cap)
        return result

    @classmethod
    def list_ids(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def is_empty(cls) -> bool:
        return len(cls._registry) == 0

    # ── 统一切面执行 ──

    @classmethod
    def _get_breaker(cls, cap: Capability) -> CircuitBreaker | None:
        group = cap.resource_group
        if group in cls._breaker_map:
            return cls._breaker_map[group]
        threshold = cap.breaker_threshold or 5
        cls._breaker_map[group] = CircuitBreaker(failure_threshold=threshold)
        return cls._breaker_map[group]

    @classmethod
    async def execute(cls, cap_id: str, **kwargs) -> ToolResult:
        """
        系统唯一的全功能切面入口。
        无论谁调用，超时、熔断、日志、耗时、异常分类全线生效。

        ReAct Agent 使用此入口，始终返回 ToolResult。
        """
        cap = cls.get(cap_id)
        budget = current_budget.get()
        breaker = cls._get_breaker(cap)
        executor = ToolExecutor(cap, budget=budget, breaker=breaker)
        return await executor.execute({}, **kwargs)

    @classmethod
    async def call(cls, cap_id: str, **kwargs):
        """
        确定流流程的便利入口。
        内部走 execute() 同一切面，但：
        - 成功：返回 result.data（裸数据）
        - 失败：raise CapabilityExecutionError

        InterviewSession / Slave / API 等确定流程使用此入口。
        """
        result = await cls.execute(cap_id, **kwargs)
        if not result.success:
            raise CapabilityExecutionError(cap_id, result.error or "未知错误")
        return result.data
