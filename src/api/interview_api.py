"""
Interview API — 模拟面试 HTTP 接口
"""
import asyncio
import uuid
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from src.agentv3.interview import InterviewSession, PersonaManager
from src.agentv3.registry import CapabilityRegistry
from src.utils.context import current_trace_id, current_caller

router = APIRouter(prefix="/api/interview", tags=["interview"])

# ── 会话存储（生产环境应替换为 Redis） ──
_sessions: dict[str, InterviewSession] = {}


class StartRequest(BaseModel):
    resume: str = ""
    jd: str = ""
    persona_id: str = "free_mode"
    max_rounds: int = 10

    @field_validator("persona_id")
    @classmethod
    def validate_persona(cls, v: str) -> str:
        if v not in PersonaManager.list_ids():
            raise ValueError(f"未知的人设ID: {v}，可选: {PersonaManager.list_ids()}")
        return v


class AnswerRequest(BaseModel):
    room_id: str
    answer: str

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("回答不能为空")
        return v.strip()


class StartResponse(BaseModel):
    room_id: str
    greeting: str
    first_question: str
    topic_id: str | None = None
    resume_analysis: dict | None = None
    jd_analysis: dict | None = None
    match_gap: dict | None = None


class AnswerResponse(BaseModel):
    round_number: int
    scores: dict
    reasoning: str
    route: str
    next_question: str | None = None
    topic_id: str | None = None
    final: bool = False


class SummaryResponse(BaseModel):
    room_id: str
    summary: dict


@router.post("/start", response_model=StartResponse)
async def start_interview(req: StartRequest, request: Request):
    trace_id = str(uuid.uuid4())
    token = current_trace_id.set(trace_id)
    caller_token = current_caller.set("interview_api_start")
    try:
        resume_result = await CapabilityRegistry.call("analyze_resume", resume_text=req.resume)
        jd_result = await CapabilityRegistry.call("analyze_jd", jd_text=req.jd)
        gap = await CapabilityRegistry.call("match_resume_jd",
            resume_analysis=resume_result, jd_analysis=jd_result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"简历/JD分析失败: {e}")
    finally:
        current_trace_id.reset(token)
        current_caller.reset(caller_token)

    first_domain = (gap.get("gap_areas", [None]) or [None])[0] or (jd_result.get("domains", [None]) or [None])[0] or "通用"
    first_topic = {
        "question_text": f"请介绍一下你在 {first_domain} 方面的经验？",
        "question_type": "initial",
        "difficulty": 2,
        "domain": first_domain,
        "topic_keywords": gap.get("gap_areas", []),
        "expected_key_points": [],
        "topic_name": first_domain,
        "topic_id": None,
    }

    session = InterviewSession(
        persona_id=req.persona_id,
        max_rounds=req.max_rounds,
    )
    await session.setup(
        resume_text=req.resume, jd_text=req.jd,
        resume_analysis=resume_result, jd_analysis=jd_result, match_gap=gap,
        first_topic=first_topic,
    )

    greeting = f"你好！我是你今天的面试官。{jd_result.get('summary', '让我们开始吧')}"
    room_id = str(uuid.uuid4())
    _sessions[room_id] = session

    return StartResponse(
        room_id=room_id,
        greeting=greeting,
        first_question=first_topic["question_text"],
        resume_analysis=resume_result,
        jd_analysis=jd_result,
        match_gap=gap,
    )


@router.post("/answer", response_model=AnswerResponse)
async def submit_answer(req: AnswerRequest, request: Request):
    session = _sessions.get(req.room_id)
    if not session:
        raise HTTPException(status_code=404, detail="面试会话不存在或已过期")

    trace_id = str(uuid.uuid4())
    token = current_trace_id.set(trace_id)
    caller_token = current_caller.set("interview_api_answer")
    try:
        result = await session.submit_answer(req.answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理回答失败: {e}")
    finally:
        current_trace_id.reset(token)
        current_caller.reset(caller_token)

    if result.get("scores"):
        round_data = {
            "room_id": req.room_id,
            "round_number": result["round_number"],
            "scores": result["scores"],
            "route": result["route"],
        }
        asyncio.create_task(
            CapabilityRegistry.call("publish_interview_event", event_data=round_data)
        )

    return AnswerResponse(
        round_number=result["round_number"],
        scores=result["scores"],
        reasoning=result.get("reasoning", ""),
        route=result["route"],
        next_question=result.get("next_question"),
        final=result["final"],
    )


@router.get("/{room_id}/summary", response_model=SummaryResponse)
async def get_summary(room_id: str):
    session = _sessions.get(room_id)
    if not session:
        raise HTTPException(status_code=404, detail="面试会话不存在或已过期")

    return SummaryResponse(
        room_id=room_id,
        summary=session.summary(),
    )


@router.get("/personas")
async def list_personas():
    return {"personas": PersonaManager.list_ids()}
