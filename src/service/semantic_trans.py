"""
语义转换服务
基于 languageConverter Skill 实现语义转换能力
"""
import os
import json
from typing import Optional, Union
from pydantic import BaseModel, Field

from src.service.llm import LLMService
from src.common.semantic_error import (
    SemanticErrorCode,
    SemanticResult,
    SemanticData,
    KeyElement,
    success_result,
    error_result,
)


class SemanticTransRequest(BaseModel):
    """语义转换请求"""
    content: str = Field(description="待转换的输入内容")
    format_type: Optional[str] = Field(
        default="formal_text",
        description="输出格式类型: formal_text/bullet_points/structured_json/question_answer/definition"
    )


class SemanticTransService:
    """语义转换服务"""
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        初始化语义转换服务
        
        Args:
            llm_service: LLM 服务实例，如果为 None 则使用默认配置创建
        """
        self.llm_service = llm_service or LLMService()
        self.skill_path = self._load_skill()
    
    def _load_skill(self) -> str:
        """加载 languageConverter skill"""
        skill_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "skill",
            "languageConverter",
            "skill.md"
        )
        with open(skill_file, "r", encoding="utf-8") as f:
            return f.read()
    
    def _build_prompt(self, content: str, format_type: str = "formal_text") -> str:
        """构建 prompt"""
        return f"""请将以下输入进行语义转换，严格遵循 languageConverter skill 的规则：

输入内容：
{content}

要求：
1. 保留原始语义，只优化表达形式，不添加原文中不存在的信息
2. 如果输入语义混乱无法转换，返回错误对象（success: false）
3. 输出格式：{format_type}

直接输出 JSON 结果，不要有任何其他文字。"""
    
    def convert(
        self,
        content: str,
        format_type: str = "formal_text"
    ) -> SemanticResult:
        """
        执行语义转换
        
        Args:
            content: 待转换内容
            format_type: 输出格式类型
            
        Returns:
            SemanticResult: 统一格式的转换结果
        """
        # 输入校验
        if not content or not content.strip():
            return error_result(
                error_code=SemanticErrorCode.INPUT_EMPTY,
                original_input=content,
                field="content",
                suggestion="请提供有效的文本内容"
            )
        
        if len(content) > 2000:
            return error_result(
                error_code=SemanticErrorCode.INPUT_TOO_LONG,
                original_input=content,
                field="content",
                suggestion="输入内容超过2000字符，请分段处理"
            )
        
        try:
            # 调用 LLM
            response = self.llm_service.invoke(
                query=self._build_prompt(content, format_type),
                system_prompt=self.skill_path
            )
            
            # 解析响应
            return self._parse_response(response, content)
            
        except Exception as e:
            return error_result(
                error_code=SemanticErrorCode.SERVICE_ERROR,
                original_input=content,
                suggestion=f"服务处理失败: {str(e)}"
            )
    
    def _parse_response(
        self,
        response: str,
        original_input: str
    ) -> SemanticResult:
        """解析 LLM 返回的 JSON 响应"""
        try:
            # 提取 JSON
            json_str = self._extract_json(response)
            data = json.loads(json_str)
            
            # 检查是否是错误响应
            if not data.get("success", True):
                error_info = data.get("error", {})
                return error_result(
                    error_code=SemanticErrorCode.SERVICE_ERROR,
                    original_input=original_input,
                    field=error_info.get("field"),
                    suggestion=error_info.get("suggestion"),
                    original_segment=error_info.get("original_segment"),
                    partial_output=data.get("partial_output"),
                )
            
            # 成功响应 - 构建 SemanticData
            key_elements = [
                KeyElement(
                    element=ke.get("element", ""),
                    value=ke.get("value", ""),
                    confidence=ke.get("confidence", 0.0)
                )
                for ke in data.get("key_elements", [])
            ]
            
            semantic_data = SemanticData(
                standardized_output=data.get("standardized_output", ""),
                language=data.get("language", "zh"),
                format_type=data.get("format_type", "formal_text"),
                key_elements=key_elements,
                confidence=data.get("confidence", 0.0),
                suggestions=data.get("suggestions", []),
            )
            
            return success_result(
                data=semantic_data,
                original_input=original_input,
            )
            
        except json.JSONDecodeError:
            return error_result(
                error_code=SemanticErrorCode.FORMAT_CONVERT_FAILED,
                original_input=original_input,
                suggestion="服务返回格式异常，无法解析"
            )
    
    def _extract_json(self, response: str) -> str:
        """从响应中提取 JSON 字符串"""
        response = response.strip()
        
        # 移除思考过程 ()
        import re
        response = re.sub(r'</think>.*?\/s', '', response, flags=re.DOTALL)
        
        # 如果直接是 JSON
        if response.startswith("{"):
            end = response.rfind("}")
            if end != -1:
                return response[:end+1]
        
        # 如果是 ```json 包裹
        if "```json" in response:
            parts = response.split("```json")
            if len(parts) > 1:
                json_part = parts[1].split("```")[0]
                return json_part.strip()
        
        # 如果是 ``` 包裹
        if "```" in response:
            parts = response.split("```")
            if len(parts) > 1:
                return parts[1].strip()
        
        return response


# 全局服务实例
_semantic_trans_service: Optional[SemanticTransService] = None


def get_semantic_trans_service() -> SemanticTransService:
    """获取语义转换服务单例"""
    global _semantic_trans_service
    if _semantic_trans_service is None:
        _semantic_trans_service = SemanticTransService()
    return _semantic_trans_service


def semantic_convert(
    content: str,
    format_type: str = "formal_text"
) -> SemanticResult:
    """便捷函数：执行语义转换"""
    return get_semantic_trans_service().convert(content, format_type)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # 加载环境变量
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    load_dotenv(env_path)
    
    print("=== 语义转换服务测试 ===")
    
    # 创建服务
    service = SemanticTransService()
    
    # 测试用例
    test_cases = [
        ("HashMap吧它底层是数组加链表实现的", "formal_text"),
        ("需要处理用户的登录请求，验证用户名密码", "bullet_points"),
        ("性能要好", "formal_text"),  # 意图不明确，应返回错误
        ("既要支持高并发又要保证数据强一致性", "formal_text"),  # 冲突，应返回错误
        ("hashmap is fast for lookup", "formal_text"),
    ]
    
    for i, (content, format_type) in enumerate(test_cases, 1):
        print(f"\n--- 测试用例 {i} ---")
        print(f"输入: {content}")
        print(f"格式: {format_type}")
        
        result = service.convert(content, format_type)
        
        if result.success:
            print(f"成功! [code={result.code}]")
            semantic_data = result.data
            print(f"输出: {semantic_data.standardized_output[:80]}...")
            print(f"置信度: {semantic_data.confidence}")
        else:
            print(f"失败! [code={result.code}]")
            print(f"错误信息: {result.error.message if result.error else 'Unknown'}")
            if result.error and result.error.suggestion:
                print(f"建议: {result.error.suggestion}")
    
    print("\n=== 测试完成 ===")
