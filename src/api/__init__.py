"""
API 层 - 统一入口
"""
from src.api.topic_api import router as topic_router
from src.api.healthcheck import router as healthcheck_router

__all__ = ["topic_router", "healthcheck_router"]