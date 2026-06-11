"""
MasterSession —— Agent 决策主体
每个 Capability 自携带 args_schema，Master 只需一行循环构建 tools。
参考 opencode 模式：tool 定义在 Capability 内部，Agent 通过模型原生 tool calling 选择。
"""
from __future__ import annotations
import uuid, json
import httpx
from langgraph.prebuilt import create_react_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph.state import CompiledStateGraph

from src.tools.llm_client import LLMClient, _clean_proxy_env
from src.agentv3.capability import Capability
from src.agentv3.registry import CapabilityRegistry
from src.agentv3.executor import ToolExecutor
from src.agentv3.protocols import ToolResult, SlaveResult
from src.agentv3.session import AgentSession, AgentGuardError
from src.agentv3.token_budget import TokenBudget
from src.agentv3.circuit_breaker import CircuitBreaker
from src.agentv3.prompt_builder import PromptBuilder
from src.agentv3.slave import SlaveSession


class MasterSession:

    def __init__(
        self,
        token_budget_total: int = 4000,
        max_iterations: int = 10,
        max_total_time_ms: int = 60_000,
        circuit_breaker_threshold: int = 5,
    ):
        self.token_budget_total = token_budget_total
        self.max_iterations = max_iterations
        self.max_total_time_ms = max_total_time_ms
        self.circuit_breaker = CircuitBreaker(failure_threshold=circuit_breaker_threshold)
        self._slave_grants: list[Capability] = []

    def grant_slave(self, *capability_ids: str):
        self._slave_grants = [CapabilityRegistry.get(cid) for cid in capability_ids]

    async def handle(self, user_input: str) -> dict:
        trace_id = str(uuid.uuid4())
        session = AgentSession(
            trace_id=trace_id, user_input=user_input,
            token_budget=TokenBudget(self.token_budget_total),
            max_iterations=self.max_iterations,
            max_total_time_ms=self.max_total_time_ms,
        )

        read_caps = CapabilityRegistry.filter(scope="read")
        if not read_caps:
            return self._error_response(trace_id, "无可用读能力")

        system_prompt = PromptBuilder.build(read_caps, session.token_budget)
        langchain_tools = self._build_tools(read_caps, session, trace_id)
        base_llm = self._build_llm()

        # ── 创建 Agent 追踪记录 ──
        await self._trace_start(trace_id, user_input)

        try:
            agent: CompiledStateGraph = create_react_agent(base_llm, langchain_tools)
            result = await agent.ainvoke({
                "messages": [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_input),
                ]
            })
            parsed = await self._parse_output(result, trace_id, session)
            await self._trace_end(trace_id, parsed, session)
            return parsed
        except AgentGuardError as e:
            await self._trace_end(trace_id, self._best_effort(session, str(e)), session)
            return self._best_effort(session, str(e))
        except Exception as e:
            await self._trace_end(trace_id, self._error_response(trace_id, str(e)), session)
            return self._error_response(trace_id, str(e))

    # ═══════════════════════════════════════════
    # tool 构建 —— 一行循环，Capability 自举
    # ═══════════════════════════════════════════

    def _build_tools(self, caps: list[Capability], session: AgentSession, trace_id: str) -> list[StructuredTool]:
        tools = []
        for cap in caps:
            if cap.args_schema is None:
                continue

            def _wrapper(c: Capability):
                async def fn(**kwargs):
                    exec_ = ToolExecutor(c, trace_id=trace_id, budget=session.token_budget, breaker=self.circuit_breaker)
                    result: ToolResult = await exec_.execute({}, **kwargs)
                    return json.dumps(result.data, ensure_ascii=False) if result.success \
                        else json.dumps({"error": result.error}, ensure_ascii=False)
                return fn

            tools.append(cap.to_langchain_tool(_wrapper(cap)))
        return tools

    def _build_llm(self) -> BaseChatModel:
        from langchain_openai import ChatOpenAI
        _clean_proxy_env()
        client = LLMClient.get_instance()
        transport = httpx.AsyncHTTPTransport(retries=0)
        return ChatOpenAI(
            model=client.model_name, temperature=0.1,
            api_key=client.api_key, base_url=client.base_url,
            http_async_client=httpx.AsyncClient(transport=transport, trust_env=False),
            http_socket_options=(),
        )

    # ═══════════════════════════════════════════
    # 输出解析 + Slave 写委托
    # ═══════════════════════════════════════════

    async def _parse_output(self, result: dict, trace_id: str, session: AgentSession) -> dict:
        messages = result.get("messages", [])
        tool_calls = self._extract_tool_calls(messages)
        tool_results = self._extract_tool_results(messages)

        # 有 generate_topic 的结果 → 触发 Slave 写
        gen = tool_results.get("generate_topic")
        if isinstance(gen, dict) and gen.get("topic"):
            return await self._handle_generated(gen, tool_results, trace_id, tool_calls)

        # 有 search 命中
        search = tool_results.get("search_knowledge")
        if isinstance(search, dict) and search.get("candidates"):
            return self._handle_recall(search, trace_id, tool_calls)

        # 只有 normalize 结果（推理中或降级）
        norm = tool_results.get("normalize_input")
        if norm:
            return self._handle_incomplete(norm, messages, trace_id, tool_calls, session)

        # 无 tool 调用 — Agent 直接返回文本
        last = messages[-1] if messages else None
        text = str(last.content) if last and hasattr(last, "content") else ""
        return self._handle_text(text, trace_id, tool_calls, session)

    def _extract_tool_calls(self, messages) -> list[dict]:
        calls = []
        for msg in messages:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    calls.append({"name": tc.get("name"), "args": tc.get("args", {})})
        return calls

    def _extract_tool_results(self, messages) -> dict[str, any]:
        results = {}
        for msg in messages:
            if isinstance(msg, ToolMessage):
                try:
                    data = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                    results[msg.name] = data
                except json.JSONDecodeError:
                    results[msg.name] = msg.content
        return results

    async def _handle_generated(self, gen: dict, tools: dict, trace_id: str, calls: list) -> dict:
        topic_info = gen.get("topic", {})
        norm = tools.get("normalize_input", {})
        if isinstance(norm, str):
            norm = json.loads(norm) if norm.startswith("{") else {}

        if self._slave_grants:
            try:
                slave_state = {
                    "generated_topic": gen,
                    "normalized": {
                        "core_concept": norm.get("core_concept", topic_info.get("topic", "")),
                        "domain": norm.get("domain", ""),
                        "keywords": norm.get("keywords", []),
                    },
                }
                slave = SlaveSession(grants=self._slave_grants)
                sr: SlaveResult = await slave.execute(slave_state)
                if sr.topic_id:
                    return {
                        "success": True, "source": "generated",
                        "topic_id": sr.topic_id,
                        "topic_name": topic_info.get("topic", ""),
                        "domain": topic_info.get("domain", ""),
                        "trace_id": trace_id, "tool_calls": calls,
                    }
            except Exception:
                pass

        return {
            "success": True, "source": "generated",
            "topic_name": topic_info.get("topic", ""),
            "domain": topic_info.get("domain", ""),
            "trace_id": trace_id, "tool_calls": calls,
        }

    def _handle_recall(self, search: dict, trace_id: str, calls: list) -> dict:
        cands = search["candidates"]
        best = cands[0] if cands else None
        return {
            "success": True, "source": "recall",
            "topic_name": best.get("core_concept", "") if best else "",
            "domain": best.get("domain", "") if best else "",
            "confidence": best.get("rrf_score") if best else None,
            "trace_id": trace_id, "candidate_count": len(cands), "tool_calls": calls,
        }

    def _handle_incomplete(self, norm, messages, trace_id, calls, session) -> dict:
        last = messages[-1] if messages else None
        text = str(last.content) if last and hasattr(last, "content") else ""
        if isinstance(norm, str) and norm.startswith("{"):
            norm = json.loads(norm)
        return {
            "success": False, "source": "incomplete",
            "message": text[:500] if text else "Agent 推理中",
            "normalized": norm, "trace_id": trace_id,
            "tool_calls": calls, "reasoning_chain": session.reasoning_chain,
        }

    def _handle_text(self, text, trace_id, calls, session) -> dict:
        if any(kw in text for kw in ("澄清", "模糊", "非技术", "无法处理", "超出范围", "闲聊")):
            return {
                "success": False, "source": "rejected",
                "message": text[:500], "trace_id": trace_id,
                "tool_calls": calls, "reasoning_chain": session.reasoning_chain,
            }
        return {
            "success": False, "source": "no_tools",
            "message": text[:500] or "Agent 未调用工具",
            "trace_id": trace_id, "tool_calls": calls,
        }

    def _best_effort(self, session: AgentSession, reason: str) -> dict:
        return {"success": False, "source": "error", "message": reason,
                "trace_id": session.trace_id, "reasoning_chain": session.reasoning_chain}

    def _error_response(self, trace_id: str, error: str) -> dict:
        return {"success": False, "source": "error", "message": error, "trace_id": trace_id}

    async def _trace_start(self, trace_id: str, user_input: str):
        try:
            from src.models.prompt_call_log import AgentTrace
            await AgentTrace.create(
                id=str(uuid.uuid4()),
                trace_id=trace_id or "", user_input=user_input or "", status="running",
            )
        except Exception:
            pass

    async def _trace_end(self, trace_id: str, result: dict, session: AgentSession):
        try:
            from src.models.prompt_call_log import AgentTrace, PromptCallLog
            trace = await AgentTrace.filter(trace_id=trace_id).first()
            if trace:
                trace.status = "success" if (result or {}).get("success") else "failed"
                trace.source = (result or {}).get("source", "error")
                trace.topic_id = (result or {}).get("topic_id")
                trace.topic_name = (result or {}).get("topic_name")
                trace.tool_calls = (result or {}).get("tool_calls", [])
                trace.reasoning_chain = getattr(session, "reasoning_chain", [])
                trace.total_duration_ms = getattr(session, "elapsed_ms", 0)
                trace.errors = (result or {}).get("errors") or []
                call_count = await PromptCallLog.filter(trace_id=trace_id).count()
                trace.llm_call_count = call_count
                await trace.save()
        except Exception:
            pass
