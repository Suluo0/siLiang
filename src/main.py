import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from tortoise.contrib.fastapi import register_tortoise
from src.config.settings import settings
from src.api.topic_api import router as topic_v1_router
from src.api.topic_api_v2 import router as topic_v2_router
from src.api.topic_api_v3 import router as topic_v3_router
from src.api.healthcheck import router as healthcheck_router
from src.controller.menuController import router as menu_router
from src.auth.api import router as auth_router
from src.agentv3.capabilities.register import register_all
from src.agentv3.registry import CapabilityRegistry

register_all()
CapabilityRegistry.freeze()

app = FastAPI(title="TopicSystem v3", version="0.3.0")

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 全局鉴权中间件 (AOP) ──
PUBLIC_PATHS = {"/", "/ping", "/docs", "/openapi.json", "/redoc",
                "/api/auth/register", "/api/auth/login",
                "/api/v1/topic/tags"}


@app.middleware("http")
async def global_auth_middleware(request: Request, call_next):
    path = request.url.path.rstrip("/")

    # 公开路径放行
    if path in PUBLIC_PATHS:
        return await call_next(request)

    # 从 Authorization header 提取 token
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "未提供认证令牌"})

    token = auth[7:]  # "Bearer " 之后的部分

    from src.auth.jwt import decode_token
    from src.models.user import User

    payload = decode_token(token)
    if not payload:
        return JSONResponse(status_code=401, content={"detail": "令牌无效或已过期"})

    user = await User.filter(id=payload["sub"], is_active=True).first()
    if not user:
        return JSONResponse(status_code=401, content={"detail": "用户不存在或已禁用"})
    if user.token_version != payload.get("ver", 0):
        return JSONResponse(status_code=401, content={"detail": "令牌版本不匹配"})

    # 注入用户到 request.state
    request.state.user = user

    # ── 配额检查 + 扣减 ──
    from src.models.user_quota import UserQuota
    quota = await UserQuota.filter(user=user).first()
    if not quota:
        quota = await UserQuota.create(id=str(uuid.uuid4()), user=user)

    path = request.url.path.rstrip("/")

    # Agent 对话扣减
    if path == "/api/v3/topic/generate" and request.method == "POST":
        if quota.agent_credits <= 0:
            return JSONResponse(status_code=403, content={"detail": "Agent 对话次数已用尽"})
        quota.agent_credits -= 1
        await quota.save()

    # 题目浏览扣减（列表 + 详情）
    if path.startswith("/api/v1/topic") or path.startswith("/api/v2/topic"):
        if quota.topic_credits <= 0:
            return JSONResponse(status_code=403, content={"detail": "题目访问次数已用尽"})
        if request.method == "GET" and ("/list" in path or len(path.split("/")) > 3):
            quota.topic_credits -= 1
            await quota.save()

    return await call_next(request)


app.include_router(topic_v1_router)
app.include_router(topic_v2_router)
app.include_router(topic_v3_router)
app.include_router(healthcheck_router)
app.include_router(auth_router)
app.include_router(menu_router)


@app.get("/")
async def root():
    return {"service": "TopicSystem v3", "status": "ok", "capabilities": len(CapabilityRegistry.list_ids())}


register_tortoise(
    app,
    db_url=settings.DATABASE_URL,
    modules={"models": ["src.models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
