"""
LLM Service 模块
提供基于 LangChain 的 LLM 调用能力
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.config.llm_config import get_model_config


class ToolInput(BaseModel):
    """通用工具输入 schema"""
    query: str = Field(description="用户查询内容")


@tool("gen", args_schema=ToolInput)
def gen(query: str) -> str:
    """通用生成工具，根据输入生成响应。"""
    return f"处理结果: {query}"


class LLMService:
    """LLM 服务类"""
    
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
        """初始化 LLM 服务"""
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
        )
        
        self.llm_with_tools = self.llm.bind_tools([gen])
    
    def bind_tools(self, tools: List) -> "LLMService":
        """绑定工具列表"""
        self.llm_with_tools = self.llm.bind_tools(tools)
        return self
    
    def invoke(
        self,
        query: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List] = None,
        json_mode: bool = False,
    ) -> str:
        """
        执行 LLM 调用
        
        Args:
            query: 用户查询
            system_prompt: 系统提示词
            tools: 工具列表
            json_mode: 是否强制返回 JSON（过滤掉<think>等内容）
            
        Returns:
            str: LLM 响应内容
        """
        messages = []
        
        if system_prompt:
            # 如果启用 json_mode，在 system_prompt 中追加 JSON 强制要求
            if json_mode:
                system_prompt = system_prompt.strip() + "\n\n重要：只输出JSON，不要输出任何<think>...思考内容或其他文字。"
            messages.append(SystemMessage(content=system_prompt))
        elif json_mode:
            messages.append(SystemMessage(content="重要：只输出JSON，不要输出任何<think>...思考内容或其他文字。"))
        
        messages.append(HumanMessage(content=query))
        
        if tools:
            llm_with_tools = self.llm.bind_tools(tools)
            ai_msg = llm_with_tools.invoke(messages)
        else:
            # 不使用绑定了 gen 工具的 llm_with_tools，直接使用 llm
            ai_msg = self.llm.invoke(messages)
        
        content = ai_msg.content
        
        # 如果启用 json_mode，过滤掉<think>...内容
        if json_mode:
            content = self._strip_think_content(content)
        
        return content
    
    def _strip_think_content(self, content: str) -> str:
        """
        过滤掉 LLM 返回内容中的<think>...思考过程
        
        Args:
            content: 原始返回内容
            
        Returns:
            str: 过滤后的内容
        """
        import re
        # 移除<think>...及其内容
        # 匹配<think>开头的内容，直到遇到第一个完整的 JSON 块或结束
        # 策略：移除所有<think>...到下一个```json或```之间的内容
        lines = []
        skip_until_json = False
        
        for line in content.split('\n'):
            if skip_until_json:
                # 跳过直到遇到 ```
                if line.strip() == '```' or line.strip() == '```json':
                    if line.strip() == '```json':
                        lines.append('```json')
                    skip_until_json = False
                continue
            
            if line.strip().startswith('<think>'):
                # 开始跳过
                if '```json' in content:
                    skip_until_json = True
                continue
            
            lines.append(line)
        
        result = '\n'.join(lines)
        
        # 如果上面策略无效，使用更激进的方法：移除所有 ```...``` 块之外的内容
        # 先移除所有<think>块
        result = re.sub(r'<think>[\s\S]*?\n\n', '', result)
        
        return result.strip()
    
    def invoke_with_history(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        tools: Optional[List] = None,
    ) -> str:
        """带历史记录的 LLM 调用"""
        langchain_messages = []
        
        if system_prompt:
            langchain_messages.append(SystemMessage(content=system_prompt))
        
        for msg in messages:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))
        
        if tools:
            llm_with_tools = self.llm.bind_tools(tools)
        else:
            llm_with_tools = self.llm_with_tools
        
        ai_msg = llm_with_tools.invoke(langchain_messages)
        return ai_msg.content


def create_llm_service(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> LLMService:
    """工厂函数：创建 LLM 服务实例"""
    return LLMService(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
        base_url=base_url,
    )


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # 加载项目根目录的 .env 文件
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    load_dotenv(env_path)
    
    print("=== LLM 模块测试 ===")
    print(f"环境变量 API_MODEL: {os.getenv('API_MODEL')}")
    print(f"环境变量 API_ADDRESS: {os.getenv('API_ADDRESS')}")
    print(f"环境变量 API_SECRET: {'***' + os.getenv('API_SECRET')[-20:] if os.getenv('API_SECRET') else None}")
    
    # 测试配置加载
    print("\n--- 模型配置 ---")
    from src.config.llm_config import list_available_models
    print(f"可用模型: {list_available_models()}")
    
    config = get_model_config("MiniMax-M2.7")
    print(f"MiniMax-M2.7 配置:")
    print(f"  - temperature: {config.temperature}")
    print(f"  - max_tokens: {config.max_tokens}")
    print(f"  - timeout: {config.timeout}")
    print(f"  - base_url: {config.base_url}")
    
    # 测试 LLM 服务创建
    print("\n--- 创建 LLM 服务 ---")
    llm = LLMService(model="MiniMax-M2.7")
    print(f"服务已创建，模型: {llm.model}")
    
    # 测试调用
    print("\n--- 测试 LLM 调用 ---")
    try:
        result = llm.invoke("你好，请介绍一下你自己", system_prompt="你是一个有用的AI助手")
        print(f"调用成功!")
        print(f"响应内容: {result[:200]}..." if len(result) > 200 else f"响应内容: {result}")
    except Exception as e:
        import traceback
        print(f"调用失败: {type(e).__name__}: {e}")
        traceback.print_exc()
    
    print("\n=== 测试完成 ===")