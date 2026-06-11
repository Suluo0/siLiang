"""
LLM 流式响应模块
提供基于 LangChain 的流式 LLM 调用能力
"""
from typing import Callable, Optional, Iterator, AsyncIterator
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import AsyncCallbackHandler

from src.config.llm_config import get_model_config


class StreamingCallbackHandler(AsyncCallbackHandler):
    """流式回调处理器"""

    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        self.callback = callback
        self.content = []

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        """LLM 输出新 token 时调用"""
        self.content.append(token)
        if self.callback:
            self.callback(token)

    def get_content(self) -> str:
        """获取累积的内容"""
        return "".join(self.content)

    def reset(self) -> None:
        """重置内容"""
        self.content = []


class LLMStreamService:
    """LLM 流式服务类"""

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """初始化 LLM 流式服务"""
        model_config = get_model_config(model)

        self.model = model or model_config.name
        self.temperature = temperature if temperature is not None else model_config.temperature
        self.max_tokens = max_tokens if max_tokens is not None else model_config.max_tokens
        self.timeout = timeout if timeout is not None else model_config.timeout
        self.max_retries = max_retries if max_retries is not None else model_config.max_retries
        self.api_key = api_key or model_config.api_key
        self.base_url = base_url or model_config.base_url

        self.llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            max_retries=self.max_retries,
            api_key=self.api_key,
            base_url=self.base_url,
            streaming=True,  # 启用流式输出
        )

    def invoke_stream(
        self,
        query: str,
        system_prompt: Optional[str] = None,
        callback: Optional[Callable[[str], None]] = None,
    ) -> Iterator[str]:
        """
        执行流式 LLM 调用（同步版本，内部使用线程池）
    
        Args:
            query: 用户查询
            system_prompt: 系统提示词
            callback: 每个 token 的回调函数
    
        Yields:
            str: LLM 响应内容（分块返回）
        """
        import anyio
            
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=query))
    
        async def async_stream():
            async for token in self.llm.astream(messages):
                if callback:
                    callback(token.content)
                yield token.content
    
        # 在线程池中运行异步生成器并转换为同步迭代器
        gen = async_stream()
        while True:
            try:
                chunk = anyio.from_thread.run_sync(gen.__anext__)
                yield chunk
            except StopAsyncIteration:
                break

    async def invoke_stream_async(
        self,
        query: str,
        system_prompt: Optional[str] = None,
        callback: Optional[Callable[[str], None]] = None,
    ) -> AsyncIterator[str]:
        """
        异步执行流式 LLM 调用

        Args:
            query: 用户查询
            system_prompt: 系统提示词
            callback: 每个 token 的回调函数

        Yields:
            str: LLM 响应内容（分块返回）
        """
        messages = []

        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        messages.append(HumanMessage(content=query))

        async for token in self.llm.astream(messages):
            if callback:
                callback(token.content)
            yield token.content

    def invoke_stream_sync(
        self,
        query: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        同步执行流式 LLM 调用，返回完整响应

        Args:
            query: 用户查询
            system_prompt: 系统提示词

        Returns:
            str: 完整的 LLM 响应
        """
        chunks = []
        for token in self.invoke_stream(query, system_prompt):
            chunks.append(token)
        return "".join(chunks)


def create_stream_service(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> LLMStreamService:
    """工厂函数：创建流式 LLM 服务实例"""
    return LLMStreamService(
        model=model,
        api_key=api_key,
        base_url=base_url,
    )


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    load_dotenv(env_path)

    print("=== LLM 流式服务测试 ===")

    stream_service = LLMStreamService(model="MiniMax-M2.7")

    print("\n--- 测试流式调用 ---")
    collected = []

    def on_token(token: str):
        collected.append(token)
        print(token, end="", flush=True)

    result = stream_service.invoke_stream_sync(
        query="请用一句话介绍 HashMap",
        system_prompt="你是一个有用的AI助手"
    )

    print(f"\n\n完整响应: {result}")
    print(f"\n=== 测试完成 ===")
