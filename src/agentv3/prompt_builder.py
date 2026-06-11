"""
PromptBuilder —— 极简 prompt，类似 opencode 的 tool list 注入
不给步骤，只给能力清单。Agent 通过 model-native tool calling 自主决策。
"""
from __future__ import annotations
from src.agentv3.capability import Capability
from src.agentv3.token_budget import TokenBudget


class PromptBuilder:

    SYSTEM = """你是一个技术面试题助手。你有一组可用的工具，根据输入自行判断需要哪些。

## 可用工具

{tools}

## 约束

- 模糊或非技术输入 → 直接澄清，不调任何工具
- 每个工具的描述中说明了适用场景和不适用场景——按此判断
- 工具成本标记: cheap/expensive/free —— 优先用 cheap
- 不要预设调用顺序，根据每一步的结果决定下一步
{budget}"""

    @classmethod
    def build(cls, caps: list[Capability], budget: TokenBudget) -> str:
        tool_lines = "\n".join(c.format_for_prompt() for c in caps)
        budget_text = f"- Token 预算: {budget.status_text()}"
        return cls.SYSTEM.format(tools=tool_lines, budget=budget_text)
