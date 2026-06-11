"""
链路追踪 — OpenTelemetry + LangFuse 初始化
"""
import os
from src.config.settings import settings

_tracing_enabled = False


def init_tracing():
    """初始化链路追踪"""
    global _tracing_enabled

    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        return False

    try:
        from langfuse.langchain import CallbackHandler
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.LANGFUSE_PUBLIC_KEY)
        os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.LANGFUSE_SECRET_KEY)
        os.environ.setdefault("LANGFUSE_HOST", settings.LANGFUSE_HOST)
        _tracing_enabled = True
        return True
    except ImportError:
        return False


def get_langfuse_handler():
    """获取 LangFuse CallbackHandler"""
    if not _tracing_enabled:
        return None
    try:
        from langfuse.langchain import CallbackHandler
        return CallbackHandler()
    except Exception:
        return None


def is_tracing_enabled() -> bool:
    return _tracing_enabled
