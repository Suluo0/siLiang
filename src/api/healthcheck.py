"""
HealthCheck API - 健康检查端点

提供 /ping 接口用于服务健康状态检查
"""
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel


class PingResponse(BaseModel):
    """Ping 响应"""
    status: str
    timestamp: str
    service: str = "TopicSystem"


router = APIRouter(tags=["healthcheck"])


@router.get("/ping", response_model=PingResponse)
async def ping():
    """
    健康检查端点
    
    Returns:
        PingResponse: 包含服务状态的响应
    """
    return PingResponse(
        status="ok",
        timestamp=datetime.now().isoformat(),
        service="TopicSystem"
    )
