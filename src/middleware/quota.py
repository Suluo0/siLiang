"""配额中间件：数据库条件 UPDATE 保证并发请求不透支。"""
import re
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from tortoise.expressions import F

_TOPIC_DETAIL = re.compile(r"^/api/topic/[0-9a-fA-F-]{36}$")


async def consume_agent_credit(user_id: str) -> bool:
    """原子消耗一次 Agent 配额。"""
    from src.models.user_quota import UserQuota

    return await UserQuota.filter(user_id=user_id, agent_credits__gt=0).update(
        agent_credits=F("agent_credits") - 1,
    ) == 1


async def quota_middleware(request: Request, call_next):
    uid = getattr(request.state, "user_id", None)
    if uid is None:
        return await call_next(request)

    from src.models.user_quota import UserQuota

    quota, _ = await UserQuota.get_or_create(
        user_id=uid,
        defaults={"id": str(uuid.uuid4()), "topic_credits": 20, "agent_credits": 5},
    )
    path = request.url.path.rstrip("/")

    if path == "/api/topic/generate" and request.method == "POST":
        if not await consume_agent_credit(uid):
            return JSONResponse(status_code=403, content={"detail": "Agent 对话次数已用尽"})

    if request.method == "GET" and _TOPIC_DETAIL.fullmatch(path):
        updated = await UserQuota.filter(id=quota.id, topic_credits__gt=0).update(
            topic_credits=F("topic_credits") - 1,
        )
        if updated != 1:
            request.state.quota_exhausted = True

    return await call_next(request)
