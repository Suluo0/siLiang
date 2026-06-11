"""
CapabilityRegistry —— 全局能力注册表
启动时注册，freeze 后不可变。
"""
from __future__ import annotations
from typing import Callable
from src.agentv3.capability import Capability
from src.agentv3.permissions import Permission


class CapabilityRegistry:
    """全局能力注册表。启动时注册所有能力，运行时不可变。"""

    _registry: dict[str, Capability] = {}
    _frozen: bool = False

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
