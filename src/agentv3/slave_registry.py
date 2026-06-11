"""
SlaveCapabilityRegistry —— Slave 白名单注册表
和 CapabilityRegistry 物理隔离，不在白名单里的能力永远不可被 Slave 调用。
"""
from __future__ import annotations


class SlaveCapabilityRegistry:
    """独立的 Slave 白名单。只有显式注册的能力可通过。"""

    _whitelist: dict[str, str] = {}  # {capability_id: reason_for_approval}

    @classmethod
    def register(cls, capability_id: str, reason: str = ""):
        cls._whitelist[capability_id] = reason

    @classmethod
    def is_allowed(cls, capability_id: str) -> bool:
        return capability_id in cls._whitelist

    @classmethod
    def list_ids(cls) -> list[str]:
        return list(cls._whitelist.keys())

    @classmethod
    def clear(cls):
        """仅用于测试"""
        cls._whitelist.clear()
