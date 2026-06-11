"""
通用结果集定义
Unified Response Schema
统一处理成功和失败的响应格式
"""
from enum import Enum
from typing import Optional, Any, Dict, List, Union
from pydantic import BaseModel, Field


class SemanticErrorCode(str, Enum):
    """结果状态码枚举"""
    
    # 成功 (0xxx)
    SUCCESS = "SEM_0000"                    # 成功
    
    # 输入错误 (1xxx)
    INPUT_EMPTY = "SEM_1001"                # 输入为空
    INPUT_TOO_LONG = "SEM_1002"             # 输入过长
    INPUT_ILLEGAL_CHAR = "SEM_1003"         # 包含非法字符
    INPUT_ENCODING_ERROR = "SEM_1004"       # 编码错误
    
    # 语义错误 (2xxx)
    SEMANTIC_AMBIGUOUS = "SEM_2001"         # 语义模糊，无法理解
    SEMANTIC_CONFLICT = "SEM_2002"          # 语义冲突，前后矛盾
    SEMANTIC_INCOMPLETE = "SEM_2003"         # 语义不完整，缺少关键要素
    SEMANTIC_UNCLEAR_INTENT = "SEM_2004"     # 意图不明确
    SEMANTIC_MULTIPLE_INTENT = "SEM_2005"    # 多重意图，无法确定优先级
    
    # 语言错误 (3xxx)
    LANGUAGE_UNSUPPORTED = "SEM_3001"        # 不支持的语言
    LANGUAGE_MIXED_ERROR = "SEM_3002"        # 中英文混合处理错误
    LANGUAGE_DETECT_FAILED = "SEM_3003"       # 语言检测失败
    
    # 格式错误 (4xxx)
    FORMAT_UNSUPPORTED = "SEM_4001"          # 不支持的输出格式
    FORMAT_CONVERT_FAILED = "SEM_4002"       # 格式转换失败
    
    # 服务错误 (5xxx)
    SERVICE_ERROR = "SEM_5001"               # 服务内部错误
    SERVICE_TIMEOUT = "SEM_5002"             # 服务超时
    SERVICE_UNAVAILABLE = "SEM_5003"          # 服务不可用


class SemanticErrorDetail(BaseModel):
    """错误详情"""
    code: str = Field(description="错误码")
    message: str = Field(description="错误信息（人类可读）")
    field: Optional[str] = Field(default=None, description="错误字段")
    suggestion: Optional[str] = Field(default=None, description="修复建议")
    original_segment: Optional[str] = Field(default=None, description="导致错误的原始片段")


class SemanticResult(BaseModel):
    """
    通用结果集
    统一成功和失败的响应格式
    """
    success: bool = Field(description="是否成功")
    code: str = Field(default="SEM_0000", description="状态码")
    message: str = Field(default="Success", description="状态信息")
    
    # 数据内容（成功时使用）
    data: Optional[Any] = Field(default=None, description="结果数据")
    
    # 错误详情（失败时使用）
    error: Optional[SemanticErrorDetail] = Field(default=None, description="错误详情")
    
    # 原始输入
    original_input: Optional[str] = Field(default=None, description="原始输入")
    
    # 部分输出
    partial_output: Optional[str] = Field(default=None, description="部分成功的结果（如果有）")
    
    # 元数据
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="额外元数据")


class KeyElement(BaseModel):
    """关键要素"""
    element: str = Field(description="要素名称")
    value: Any = Field(description="要素值")
    confidence: float = Field(ge=0.0, le=1.0, description="置信度")


class SemanticData(BaseModel):
    """
    语义转换结果数据
    作为 SemanticResult.data 的内容
    """
    standardized_output: str = Field(description="标准化输出")
    language: str = Field(description="输出语言 (zh/en)")
    format_type: str = Field(description="输出格式类型")
    key_elements: List[KeyElement] = Field(default_factory=list, description="关键要素列表")
    confidence: float = Field(ge=0.0, le=1.0, description="置信度")
    suggestions: List[str] = Field(default_factory=list, description="优化建议")


def success_result(
    data: Union[SemanticData, Any],
    code: str = "SEM_0000",
    message: str = "Success",
    original_input: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> SemanticResult:
    """创建成功结果的便捷函数"""
    return SemanticResult(
        success=True,
        code=code,
        message=message,
        data=data,
        error=None,
        original_input=original_input,
        partial_output=None,
        metadata=metadata,
    )


def error_result(
    error_code: SemanticErrorCode,
    original_input: Optional[str] = None,
    field: Optional[str] = None,
    suggestion: Optional[str] = None,
    original_segment: Optional[str] = None,
    partial_output: Optional[str] = None,
    data: Optional[Any] = None,
) -> SemanticResult:
    """创建错误结果的便捷函数"""
    return SemanticResult(
        success=False,
        code=error_code.value,
        message=error_code.name.replace("_", " "),
        data=data,
        error=SemanticErrorDetail(
            code=error_code.value,
            message=error_code.name.replace("_", " "),
            field=field,
            suggestion=suggestion,
            original_segment=original_segment,
        ),
        original_input=original_input,
        partial_output=partial_output,
    )


# 向后兼容：保留旧的类名作为别名
SemanticErrorResponse = SemanticResult
SemanticSuccessResponse = SemanticResult


# 错误码详情映射表
ERROR_CODE_DETAILS: Dict[str, Dict[str, str]] = {
    "SEM_0000": {"name": "成功", "description": "处理成功完成"},
    "SEM_1001": {"name": "输入为空", "description": "用户输入内容为空"},
    "SEM_1002": {"name": "输入过长", "description": "超过2000字符限制"},
    "SEM_1003": {"name": "包含非法字符", "description": "包含无法处理的特殊字符"},
    "SEM_2001": {"name": "语义模糊", "description": "无法理解意图"},
    "SEM_2002": {"name": "语义冲突", "description": "前后矛盾"},
    "SEM_2003": {"name": "语义不完整", "description": "缺少关键要素"},
    "SEM_2004": {"name": "意图不明确", "description": "无法确定目标"},
    "SEM_2005": {"name": "多重意图", "description": "多个不同意图"},
    "SEM_3001": {"name": "不支持的语言", "description": "非中英文"},
    "SEM_5001": {"name": "服务内部错误", "description": "处理过程中发生错误"},
    "SEM_5002": {"name": "服务超时", "description": "处理超时"},
}
