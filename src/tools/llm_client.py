"""
统一 LLM 客户端
"""
import os
from typing import Optional, Type
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
import httpx

from src.config.settings import settings


def _clean_proxy_env():
    """清除系统代理环境变量，避免 httpx 强制走代理"""
    for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
        os.environ.pop(key, None)


class LLMClient:
    _instance: Optional["LLMClient"] = None

    def __init__(self):
        self.api_key = os.getenv("TS_DS_APIKEY", settings.LLM_API_KEY)
        self.base_url = os.getenv("API_ADDRESS", settings.LLM_API_BASE)
        self.model_name = os.getenv("API_MODEL", settings.LLM_MODEL)

    @classmethod
    def get_instance(cls) -> "LLMClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _new_async_client(self) -> httpx.AsyncClient:
        transport = httpx.AsyncHTTPTransport(retries=0)
        return httpx.AsyncClient(transport=transport, trust_env=False)

    def invoke(self, query: str, system_prompt: Optional[str] = None,
               temperature: float = 0.1, max_tokens: int = 2048, json_mode: bool = False) -> str:
        llm = ChatOpenAI(
            model=self.model_name, temperature=temperature, max_tokens=max_tokens,
            api_key=self.api_key, base_url=self.base_url,
            model_kwargs={"response_format": {"type": "json_object"}} if json_mode else {},
        )
        msgs = [SystemMessage(content=system_prompt)] if system_prompt else []
        msgs.append(HumanMessage(content=query))
        return llm.invoke(msgs).content

    async def ainvoke(self, query: str, system_prompt: Optional[str] = None,
                      temperature: float = 0.1, max_tokens: int = 2048, json_mode: bool = False) -> str:
        _clean_proxy_env()
        llm = ChatOpenAI(
            model=self.model_name, temperature=temperature, max_tokens=max_tokens,
            api_key=self.api_key, base_url=self.base_url,
            http_async_client=self._new_async_client(),
            http_socket_options=(),  # 阻止 langchain 注入 socket 选项（会重置代理设置）
            model_kwargs={"response_format": {"type": "json_object"}} if json_mode else {},
        )
        msgs = [SystemMessage(content=system_prompt)] if system_prompt else []
        msgs.append(HumanMessage(content=query))
        return (await llm.ainvoke(msgs)).content
