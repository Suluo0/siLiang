"""
配额中间件 — 检查并扣减用户 agent/topic 额度
"""
import uuid
from fastapi import Request
from fastapi.responses import JSONResponse


async def quota_middleware(request: Request, call_next):
    uid = getattr(request.state, "user_id", None)
    if uid is None:
        return await call_next(request)

    from src.models.user_quota import UserQuota

    quota = await UserQuota.filter(user_id=uid).first()
    if not quota:
        quota = await UserQuota.create(id=str(uuid.uuid4()), user_id=uid)

    path = request.url.path.rstrip("/")

    # Agent 对话扣减
    if path == "/api/topic/generate" and request.method == "POST":
        if quota.agent_credits <= 0:
            return JSONResponse(status_code=403, content={"detail": "Agent 对话次数已用尽"})
        quota.agent_credits -= 1
        await quota.save()

    # 题目浏览扣减（仅详情页，列表页不扣）
    if request.method == "GET" and path.startswith("/api/topic/") and "/list" not in path and "/tags" not in path:
        if quota.topic_credits <= 0:
            request.state.quota_exhausted = True
        else:
            quota.topic_credits -= 1
            await quota.save()

    return await call_next(request)
