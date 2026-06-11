import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from tortoise.contrib.fastapi import register_tortoise
from src.config.settings import settings
from src.api.topic_api import router as topic_v1_router
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
                "/api/auth/register", "/api/auth/login", "/api/auth/refresh",
                "/api/auth/captcha", "/api/auth/send-code",
                "/api/v1/topic/tags", "/api/v1/topic/positions"}


@app.middleware("http")
async def global_auth_middleware(request: Request, call_next):
    path = request.url.path.rstrip("/") or "/"

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

    uid = payload["sub"]
    # 用户缓存（60s），减少 DB 查询
    from src.api.cache import cache as user_cache
    user = user_cache.get(f"user_{uid}")
    if user is None:
        user = await User.filter(id=uid, is_active=True).first()
        if user:
            user_cache.set(f"user_{uid}", {
                "id": str(user.id), "token_version": user.token_version, "is_active": user.is_active
            }, ttl=60)
        else:
            return JSONResponse(status_code=401, content={"detail": "用户不存在或已禁用"})
    else:
        if user.get("token_version", 0) != payload.get("ver", 0):
            user_cache.set(f"user_{uid}", None, ttl=1)  # 失效缓存
            return JSONResponse(status_code=401, content={"detail": "令牌版本不匹配"})
        if not user.get("is_active"):
            return JSONResponse(status_code=401, content={"detail": "用户不存在或已禁用"})

    # 注入到 request.state（协程局部）
    request.state.user_id = uid
    request.state.user_token_version = payload.get("ver", 0)

    # 注入用户到 request.state
    request.state.user = user

    # ── 配额检查 + 扣减 ──
    from src.models.user_quota import UserQuota
    quota = await UserQuota.filter(user_id=uid).first()
    if not quota:
        quota = await UserQuota.create(id=str(uuid.uuid4()), user_id=uid)

    path = request.url.path.rstrip("/")
    # Agent 对话扣减
    if path == "/api/v3/topic/generate" and request.method == "POST":
        if quota.agent_credits <= 0:
            return JSONResponse(status_code=403, content={"detail": "Agent 对话次数已用尽"})
        quota.agent_credits -= 1
        await quota.save()
    # 题目浏览扣减（仅详情页，列表页不扣）
    if request.method == "GET" and path.startswith("/api/v1/topic/") and "/list" not in path and "/tags" not in path:
        if quota.topic_credits <= 0:
            request.state.quota_exhausted = True  # 标记 → detail 端点截断
        else:
            quota.topic_credits -= 1
            await quota.save()

    return await call_next(request)


app.include_router(topic_v1_router)
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
