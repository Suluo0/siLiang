"""
SlaveSession —— 独立事务上下文
Master 显式授予能力后，Slave 在隔离环境中执行写入。
"""
from __future__ import annotations
import asyncio
import copy
from src.agentv3.slave_registry import SlaveCapabilityRegistry
from src.agentv3.capability import Capability
from src.agentv3.protocols import SlaveResult, FailedCap


class SlavePermissionError(Exception):
    pass


class SlaveSession:
    """Master 创建 Slave 时必须显式授予能力清单。
    不在白名单的能力、scope≠write 的能力一律不可用。"""

    max_invocations_per_tool: int = 1
    total_max_invocations: int = 3

    def __init__(self, grants: list[Capability]):
        self.tools: dict[str, Capability] = {}
        self._invocation_count: dict[str, int] = {}
        for cap in grants:
            if not SlaveCapabilityRegistry.is_allowed(cap.id):
                raise SlavePermissionError(
                    f"{cap.id} 不在 Slave 白名单中，不可授予"
                )
            if cap.scope != "write":
                raise SlavePermissionError(
                    f"{cap.id} (scope={cap.scope}) 不是写能力，不可授予 Slave"
                )
            self.tools[cap.id] = cap

    async def execute(self, state_copy: dict) -> SlaveResult:
        """在事务隔离中执行所有授予的能力。一个失败全部回滚。"""
        completed = []
        failed = []

        # 深拷贝 —— Slave 无法修改 Master 上下文
        state = copy.deepcopy(state_copy)

        for cap_id, cap in self.tools.items():
            # 调用次数限制
            count = self._invocation_count.get(cap_id, 0)
            if count >= self.max_invocations_per_tool:
                failed.append(FailedCap(cap.id, f"已调用 {self.max_invocations_per_tool} 次", False))
                continue
            if sum(self._invocation_count.values()) >= self.total_max_invocations:
                failed.append(FailedCap(cap.id, "Slave 总调用次数已达上限", False))
                continue

            # 异常隔离 —— Slave 崩溃不影响 Master
            try:
                kwargs = self._build_kwargs(cap_id, state)
                if asyncio.iscoroutinefunction(cap.handler):
                    result = await cap.handler(**kwargs)
                else:
                    result = cap.handler(**kwargs)
                self._invocation_count[cap_id] = count + 1
                completed.append(cap_id)
                self._update_state(state, result)
            except Exception as e:
                failed.append(FailedCap(cap.id, str(e), False))

        topic_id = state.get("_topic_id") or state.get("topic_id")
        compensable = any(
            f.capability_id == "save_to_milvus" and f.error
            for f in failed
        )

        return SlaveResult(
            success=len(completed) == len(self.tools),
            partial=len(completed) > 0 and len(failed) > 0,
            completed=completed,
            failed=failed,
            compensable=compensable,
            topic_id=topic_id,
        )

    def _build_kwargs(self, cap_id: str, state: dict) -> dict:
        """根据 capability ID 从 state 中提取参数"""
        if cap_id == "save_to_postgres":
            return {"topic_data": state.get("generated_topic", {})}
        if cap_id == "save_to_milvus":
            norm = state.get("normalized", {})
            return {
                "topic_id": state.get("_topic_id", ""),
                "core_concept": norm.get("core_concept", ""),
                "domain": norm.get("domain", ""),
                "keywords": ",".join(norm.get("keywords", [])),
                "difficulty": state.get("generated_topic", {}).get("topic", {}).get("difficulty", 3),
            }
        raise ValueError(f"未知的 Slave capability: {cap_id}")

    def _update_state(self, state: dict, result: dict):
        """将 capability 的结果写回 state（用于下一个 capability）"""
        if result.get("topic_id"):
            state["_topic_id"] = result["topic_id"]
        if result.get("created"):
            state["_created"] = True
