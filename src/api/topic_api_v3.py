"""
Topic API v3 — Agent Loop 入口
POST /api/v3/topic/generate
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from src.agentv3.master import MasterSession

router = APIRouter(prefix="/api/v3/topic", tags=["topic-v3"])


class GenerateRequest(BaseModel):
    user_input: str

    @field_validator("user_input")
    @classmethod
    def validate_input(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 2:
            raise ValueError("输入过短，请提供更具体的技术概念")
        if len(stripped) > 500:
            raise ValueError("输入过长，请精简到 500 字符以内")
        if stripped.isdigit() or all(not c.isalnum() for c in stripped):
            raise ValueError("请输入有效的技术概念，而非数字或符号")
        return stripped


class GenerateResponse(BaseModel):
    success: bool
    source: str | None = None
    topic_id: str | None = None
    topic_name: str | None = None
    domain: str | None = None
    confidence: float | None = None
    trace_id: str | None = None
    message: str | None = None


@router.post("/generate", response_model=GenerateResponse)
async def generate_topic(req: GenerateRequest):
    try:
        master = MasterSession()
        master.grant_slave("save_to_postgres", "save_to_milvus")
        result = await master.handle(req.user_input)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent 执行失败: {e}")

    return GenerateResponse(
        success=result.get("success", False),
        source=result.get("source"),
        topic_id=result.get("topic_id"),
        topic_name=result.get("topic_name"),
        domain=result.get("domain"),
        confidence=result.get("confidence"),
        trace_id=result.get("trace_id"),
        message=result.get("message"),
    )
