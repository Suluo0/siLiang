"""
Capability 数据模型 —— 每个能力自携带 schema + 自举方法
设计参考 opencode/claude 的 tool 定义模式
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Any, Literal
from enum import StrEnum

from pydantic import BaseModel
from src.agentv3.permissions import Permission


class CostTier(StrEnum):
    FREE = "free"
    CHEAP = "cheap"
    EXPENSIVE = "expensive"


@dataclass
class Capability:
    """一个自举的能力单元。新增能力只需实例化 + 注册，无需改任何其他代码。"""

    id: str
    name: str
    description: str
    when_relevant: str
    when_irrelevant: str
    permissions: list[Permission]
    scope: Literal["read", "write"]
    handler: Callable

    # 参数 schema — 驱动 LangChain StructuredTool 的 arg 定义
    # 新增能力时必须提供，Agent 用这个 schema 理解如何传参
    args_schema: type[BaseModel] | None = None

    # 元信息
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    requires_prerequisite: list[str] = field(default_factory=list)
    precondition: Callable[..., bool] | None = None
    estimated_cost: CostTier = CostTier.CHEAP
    estimated_latency_ms: int = 100
    fallback: str | None = None

    def format_for_prompt(self) -> str:
        """一行描述，类似 opencode skill 的 metadata"""
        cost = f"({self.estimated_cost}, {self.estimated_latency_ms}ms)"
        return f"- {self.id}: {self.description} {cost}"

    def tool_description(self) -> str:
        """给 LangChain tool 的完整描述"""
        parts = [
            self.description,
            f"何时使用: {self.when_relevant}",
            f"何时不用: {self.when_irrelevant}",
        ]
        if self.depends_on:
            parts.append(f"前置依赖: {', '.join(self.depends_on)}")
        return ". ".join(parts)

    def to_langchain_tool(self, handler_wrapper: Callable):
        """自举——返回 LangChain StructuredTool，无需外部组装"""
        from langchain_core.tools import StructuredTool

        return StructuredTool.from_function(
            coroutine=handler_wrapper,
            name=self.id,
            description=self.tool_description(),
            args_schema=self.args_schema,
        )
