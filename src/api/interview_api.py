"""模拟面试 HTTP API：会话持久化、所有权校验和乐观并发控制。"""
import asyncio
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from tortoise.expressions import F

from src.agentv3.interview import InterviewSession, PersonaManager
from src.agentv3.registry import CapabilityRegistry
from src.models.interview_room import InterviewRoom
from src.utils.context import current_trace_id, current_caller

router = APIRouter(prefix="/api/interview", tags=["interview"])
_background_tasks: set[asyncio.Task] = set()
SESSION_TTL = timedelta(hours=2)


class StartRequest(BaseModel):
    resume: str = Field(default="", max_length=20_000)
    jd: str = Field(default="", max_length=20_000)
    persona_id: str = "free_mode"
    max_rounds: int = Field(default=10, ge=1, le=20)

    @field_validator("persona_id")
    @classmethod
    def validate_persona(cls, value: str) -> str:
        if value not in PersonaManager.list_ids():
            raise ValueError(f"未知的人设ID: {value}")
        return value


class AnswerRequest(BaseModel):
    room_id: str
    answer: str = Field(min_length=1, max_length=10_000)

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("回答不能为空")
        return value.strip()


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


def _user_id(request: Request) -> str:
    value = getattr(request.state, "user_id", None)
    if not value:
        raise HTTPException(status_code=401, detail="需要登录")
    return str(value)


def _load_session(room: InterviewRoom) -> InterviewSession:
    if not room.session_state:
        raise HTTPException(status_code=404, detail="面试会话不存在或已过期")
    return InterviewSession(**room.session_state)


@router.post("/start", response_model=StartResponse)
async def start_interview(req: StartRequest, request: Request):
    uid = _user_id(request)
    trace_id = str(uuid.uuid4())
    token = current_trace_id.set(trace_id)
    caller_token = current_caller.set("interview_api_start")
    try:
        resume_result = await CapabilityRegistry.call("analyze_resume", resume_text=req.resume)
        jd_result = await CapabilityRegistry.call("analyze_jd", jd_text=req.jd)
        gap = await CapabilityRegistry.call(
            "match_resume_jd", resume_analysis=resume_result, jd_analysis=jd_result,
        )
    except Exception:
        raise HTTPException(status_code=503, detail="面试分析服务暂时不可用")
    finally:
        current_trace_id.reset(token)
        current_caller.reset(caller_token)

    first_domain = (gap.get("gap_areas", [None]) or [None])[0] or (jd_result.get("domains", [None]) or [None])[0] or "通用"
    first_topic = {
        "question_text": f"请介绍一下你在 {first_domain} 方面的经验？",
        "question_type": "initial", "difficulty": 2, "domain": first_domain,
        "topic_keywords": gap.get("gap_areas", []), "expected_key_points": [],
        "topic_name": first_domain, "topic_id": None,
    }
    session = InterviewSession(persona_id=req.persona_id, max_rounds=req.max_rounds)
    await session.setup(
        resume_text=req.resume, jd_text=req.jd, resume_analysis=resume_result,
        jd_analysis=jd_result, match_gap=gap, first_topic=first_topic,
    )
    room_id = str(uuid.uuid4())
    await InterviewRoom.create(
        id=room_id, user_id=uid, persona_id=req.persona_id,
        target_position=first_domain, jd_text=req.jd, resume_text=req.resume,
        jd_analysis=jd_result, resume_analysis=resume_result, match_gap=gap,
        session_state=asdict(session), expires_at=datetime.now(timezone.utc) + SESSION_TTL,
    )
    return StartResponse(
        room_id=room_id,
        greeting=f"你好！我是你今天的面试官。{jd_result.get('summary', '让我们开始吧')}",
        first_question=first_topic["question_text"], resume_analysis=resume_result,
        jd_analysis=jd_result, match_gap=gap,
    )


@router.post("/answer", response_model=AnswerResponse)
async def submit_answer(req: AnswerRequest, request: Request):
    uid = _user_id(request)
    room = await InterviewRoom.filter(id=req.room_id, user_id=uid, status="active").first()
    if not room or (room.expires_at and room.expires_at <= datetime.now(timezone.utc)):
        raise HTTPException(status_code=404, detail="面试会话不存在或已过期")
    original_version = room.version
    session = _load_session(room)

    trace_id = str(uuid.uuid4())
    token = current_trace_id.set(trace_id)
    caller_token = current_caller.set("interview_api_answer")
    try:
        result = await session.submit_answer(req.answer)
    except Exception:
        raise HTTPException(status_code=503, detail="回答处理服务暂时不可用")
    finally:
        current_trace_id.reset(token)
        current_caller.reset(caller_token)

    updated = await InterviewRoom.filter(
        id=room.id, user_id=uid, version=original_version,
    ).update(
        session_state=asdict(session), version=F("version") + 1,
        total_rounds=session.round_number,
        expires_at=datetime.now(timezone.utc) + SESSION_TTL,
    )
    if updated != 1:
        raise HTTPException(status_code=409, detail="正在处理上一轮回答，请稍候")

    if result.get("scores"):
        task = asyncio.create_task(CapabilityRegistry.call(
            "publish_interview_event",
            event_data={"room_id": req.room_id, "round_number": result["round_number"],
                        "scores": result["scores"], "route": result["route"]},
        ))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    return AnswerResponse(
        round_number=result["round_number"], scores=result["scores"],
        reasoning=result.get("reasoning", ""), route=result["route"],
        next_question=result.get("next_question"), final=result["final"],
    )


@router.get("/{room_id}/summary", response_model=SummaryResponse)
async def get_summary(room_id: str, request: Request):
    uid = _user_id(request)
    room = await InterviewRoom.filter(id=room_id, user_id=uid).first()
    if not room or (room.expires_at and room.expires_at <= datetime.now(timezone.utc)):
        raise HTTPException(status_code=404, detail="面试会话不存在或已过期")
    return SummaryResponse(room_id=room_id, summary=_load_session(room).summary())


@router.get("/personas")
async def list_personas():
    return {"personas": PersonaManager.list_ids()}
