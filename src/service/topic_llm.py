"""
Topic LLM 服务
负责调用 LLM 生成面试题数据
"""
import os
import json
import re
import datetime
from typing import Optional, Iterator, AsyncIterator

from src.service.llm import LLMService
from src.service.llm_stream import LLMStreamService


class TopicLLMService:
    """Topic LLM 服务 - 负责调用 LLM 生成数据"""
    
    def __init__(self, llm_service: Optional[LLMService] = None, llm_stream_service: Optional[LLMStreamService] = None):
        self.llm_service = llm_service or LLMService()
        self.llm_stream_service = llm_stream_service or LLMStreamService()
        self.skill_path = self._load_gen_skill()
    
    def _load_gen_skill(self) -> str:
        """加载 generateByTopic skill v2"""
        skill_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "skill",
            "generateByTopic",
            "skill_v2.md"
        )
        with open(skill_file, "r", encoding="utf-8") as f:
            return f.read()
    
    def generate_topic(self, standardized_input: str, save_response: bool = True) -> dict:
        """
        调用 llm+skill 生成面试题
        
        Args:
            standardized_input: 标准化后的输入
            save_response: 是否保存 LLM 响应到文件
            
        Returns:
            dict: 解析后的 JSON 数据
        """
        prompt = f"""请根据以下输入生成完整的面试题数据，严格遵循 generateByTopic skill 的规则：

输入内容：
{standardized_input}

直接输出 JSON 结果，不要有任何其他文字。"""
        
        # 调用 LLM（启用 json_mode 强制返回 JSON，过滤<think>内容）
        response = self.llm_service.invoke(
            query=prompt,
            system_prompt=self.skill_path,
            json_mode=True
        )
        
        # 保存 LLM 原始响应
        if save_response:
            self._save_llm_response(response, standardized_input)
        
        # 解析 JSON
        return self._parse_json_response(response)
    
    def generate_topic_streaming(self, standardized_input: str) -> Iterator[str]:
        """
        流式调用 llm+skill 生成面试题
        
        Args:
            standardized_input: 标准化后的输入
            
        Yields:
            str: LLM 返回的内容块
        """
        prompt = f"""请根据以下输入生成完整的面试题数据，严格遵循 generateByTopic skill 的规则：

输入内容：
{standardized_input}

直接输出 JSON 结果，不要有任何其他文字。"""
        
        for chunk in self.llm_stream_service.invoke_stream(prompt, system_prompt=self.skill_path):
            yield chunk
    
    async def generate_topic_streaming_async(self, standardized_input: str) -> AsyncIterator[str]:
        """
        异步流式调用 llm+skill 生成面试题

        Args:
            standardized_input: 标准化后的输入

        Yields:
            str: LLM 返回的内容块
        """
        prompt = f"""请根据以下输入生成完整的面试题数据，严格遵循 generateByTopic skill 的规则：

输入内容：
{standardized_input}

直接输出 JSON 结果，不要有任何其他文字。"""

        async for chunk in self.llm_stream_service.invoke_stream_async(prompt, system_prompt=self.skill_path):
            yield chunk

    async def generate_topic_and_get_chunks(self, standardized_input: str, save_chunks_callback=None) -> dict:
        """
        调用 LLM 获取完整数据，同时支持流式回调

        Args:
            standardized_input: 标准化后的输入
            save_chunks_callback: 可选的回调函数，接收每个 chunk

        Returns:
            dict: 解析后的 JSON 数据
        """
        prompt = f"""请根据以下输入生成完整的面试题数据，严格遵循 generateByTopic skill 的规则：

输入内容：
{standardized_input}

直接输出 JSON 结果，不要有任何其他文字。"""

        full_response = ''
        async for chunk in self.llm_stream_service.invoke_stream_async(prompt, system_prompt=self.skill_path):
            full_response += chunk
            if save_chunks_callback:
                save_chunks_callback(chunk)

        return self._parse_json_response(full_response)

    def generate_topic(self, standardized_input: str, save_response: bool = True) -> dict:
        """保存 LLM 响应到文件"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_input = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in standardized_input[:20])
        filename = f"面试题_{safe_input}_{timestamp}.json"
        
        output_dir = os.path.join(os.path.dirname(__file__), "json_output")
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(response)
        print(f"  [DEBUG] LLM 响应已保存到: {filepath}")
    
    def _parse_json_response(self, response: str) -> dict:
        """解析 LLM 返回的 JSON 响应"""
        response = response.strip()
        
        # 移除思考过程 (<think>... 及其后的换行)
        response = re.sub(r'<think>[\\s\\S]*?\\/s*', '', response)
        
        # 移除 markdown 代码块标记
        cleaned = re.sub(r'`{3}\w*\n?', '', response)
        
        # 查找所有完整的 JSON 对象
        json_objects = []
        stack = []
        start = -1
        
        for i, c in enumerate(cleaned):
            if c == '{':
                if not stack:
                    start = i
                stack.append(c)
            elif c == '}':
                if stack:
                    stack.pop()
                    if not stack and start != -1:
                        json_objects.append((start, i + 1))
        
        # 尝试解析每个找到的 JSON 对象，从最后一个开始（通常最完整）
        for s, e in reversed(json_objects):
            candidate = cleaned[s:e]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
            
            try:
                fixed = self._fix_unescaped_newlines(candidate)
                return json.loads(fixed)
            except json.JSONDecodeError:
                continue
        
        raise ValueError("无法从响应中提取有效的 JSON 数据")
    
    def _fix_unescaped_newlines(self, json_str: str) -> str:
        """修复 JSON 中未转义的换行符和特殊字符"""
        result = []
        i = 0
        in_string = False
        skip_next_quote = False
        
        while i < len(json_str):
            c = json_str[i]
            
            if skip_next_quote:
                if c == '"':
                    skip_next_quote = False
                    in_string = True
                    result.append(c)
                    i += 1
                    continue
            
            if not in_string:
                if c == '"':
                    in_string = True
                    result.append(c)
                elif c == '\\' and i + 1 < len(json_str):
                    result.append(c)
                    result.append(json_str[i + 1])
                    i += 1
                elif c in ('\n', '\r'):
                    result.append(c)
                else:
                    result.append(c)
            else:
                if c == '\\' and i + 1 < len(json_str):
                    next_c = json_str[i + 1]
                    if next_c in ('n', 'r', 't', '\\', '"', "'"):
                        result.append(c)
                        result.append(next_c)
                        i += 1
                    else:
                        result.append(c)
                elif c == '"':
                    in_string = False
                    result.append(c)
                    j = i + 1
                    while j < len(json_str) and json_str[j] in (' ', '\t', '\n', '\r'):
                        j += 1
                    if j < len(json_str) and json_str[j] == '"':
                        skip_next_quote = True
                elif c in ('\n', '\r'):
                    result.append('\\n')
                else:
                    result.append(c)
            
            i += 1
        
        return ''.join(result)


if __name__ == "__main__":
    # 测试代码
    service = TopicLLMService()
    print("TopicLLMService 已加载")