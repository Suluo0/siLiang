"""
统一 LLM 客户端 —— 唯一 LLM 通信入口
所有参数由调用方传入，不预设业务逻辑
"""
import os
from typing import Optional, AsyncIterator
import httpx
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


def _clean_proxy_env():
    for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
        os.environ.pop(key, None)


class LLMClient:
    _instance: Optional["LLMClient"] = None

    def __init__(self):
        self.api_key = os.getenv("TS_DS_APIKEY", "")
        self.base_url = os.getenv("API_ADDRESS", "https://api.deepseek.com/v1")
        self.model_name = os.getenv("API_MODEL", "deepseek-chat")

    @classmethod
    def get_instance(cls) -> "LLMClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _new_async_client(self) -> httpx.AsyncClient:
        transport = httpx.AsyncHTTPTransport(retries=0)
        return httpx.AsyncClient(transport=transport, trust_env=False)

    # ── 同步 ──

    def invoke(self, query: str, system_prompt: Optional[str] = None,
               temperature: float = 0.1, max_tokens: int = 2048,
               json_mode: bool = False) -> str:
        llm = ChatOpenAI(model=self.model_name, temperature=temperature,
                         max_tokens=max_tokens, api_key=self.api_key,
                         base_url=self.base_url,
                         model_kwargs={"response_format": {"type": "json_object"}} if json_mode else {})
        msgs = [SystemMessage(content=system_prompt)] if system_prompt else []
        msgs.append(HumanMessage(content=query))
        return llm.invoke(msgs).content

    # ── 异步 ──

    async def ainvoke(self, query: str, system_prompt: Optional[str] = None,
                      temperature: float = 0.1, max_tokens: int = 2048,
                      json_mode: bool = False) -> str:
        _clean_proxy_env()
        llm = ChatOpenAI(model=self.model_name, temperature=temperature,
                         max_tokens=max_tokens, api_key=self.api_key,
                         base_url=self.base_url,
                         http_async_client=self._new_async_client(),
                         http_socket_options=(),
                         model_kwargs={"response_format": {"type": "json_object"}} if json_mode else {})
        msgs = [SystemMessage(content=system_prompt)] if system_prompt else []
        msgs.append(HumanMessage(content=query))
        return (await llm.ainvoke(msgs)).content

    # ── 流式 ──

    async def astream(self, query: str, system_prompt: Optional[str] = None,
                      temperature: float = 0.1, max_tokens: int = 2048) -> AsyncIterator[str]:
        """异步流式输出，yield 每个 token"""
        _clean_proxy_env()
        llm = ChatOpenAI(model=self.model_name, temperature=temperature,
                         max_tokens=max_tokens, api_key=self.api_key,
                         base_url=self.base_url, streaming=True,
                         http_async_client=self._new_async_client(),
                         http_socket_options=())
        msgs = [SystemMessage(content=system_prompt)] if system_prompt else []
        msgs.append(HumanMessage(content=query))
        async for chunk in llm.astream(msgs):
            if chunk.content:
                yield chunk.content

    # ── 结构化输出 ──

    async def ainvoke_structured(self, query: str, output_schema,
                                 system_prompt: Optional[str] = None,
                                 temperature: float = 0.1) -> dict:
        """异步结构化输出（Pydantic model）"""
        _clean_proxy_env()
        llm = ChatOpenAI(model=self.model_name, temperature=temperature,
                         api_key=self.api_key, base_url=self.base_url,
                         http_async_client=self._new_async_client(),
                         http_socket_options=())
        structured = llm.with_structured_output(output_schema)
        msgs = [SystemMessage(content=system_prompt)] if system_prompt else []
        msgs.append(HumanMessage(content=query))
        result = await structured.ainvoke(msgs)
        return result.model_dump()
