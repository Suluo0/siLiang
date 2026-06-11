"""
Topic API v2 — Agent Loop 入口
POST /api/v2/topic/generate
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from src.agent.graph import run_agent

router = APIRouter(prefix="/api/v2/topic", tags=["topic"])


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
        # 纯数字/纯符号拒绝
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
        result = await run_agent(req.user_input)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent 执行失败: {e}")

    response = result.get("response", {})
    if not response:
        raise HTTPException(status_code=500, detail="Agent 未返回响应")

    return GenerateResponse(**response)
