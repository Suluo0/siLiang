"""
Common 模块
通用工具和错误定义
"""
from .semantic_error import (
    SemanticErrorCode,
    SemanticErrorDetail,
    SemanticResult,
    SemanticData,
    KeyElement,
    SemanticErrorResponse,
    SemanticSuccessResponse,
    success_result,
    error_result,
    ERROR_CODE_DETAILS,
)

__all__ = [
    "SemanticErrorCode",
    "SemanticErrorDetail",
    "SemanticResult",
    "SemanticData",
    "KeyElement",
    "SemanticErrorResponse",
    "SemanticSuccessResponse",
    "success_result",
    "error_result",
    "ERROR_CODE_DETAILS",
]
