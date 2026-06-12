"""
认证中间件 — 全局 JWT 校验 + 用户注入
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from src.auth.deps import PUBLIC_PATHS


async def auth_middleware(request: Request, call_next):
    path = request.url.path.rstrip("/") or "/"

    # 公开路径放行
    if path in PUBLIC_PATHS:
        return await call_next(request)

    # 从 Authorization header 提取 token
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return await call_next(request)

    token = auth[7:]  # "Bearer " 之后的部分

    from src.auth.jwt import decode_token
    from src.models.user import User

    payload = decode_token(token)
    if not payload:
        return JSONResponse(status_code=401, content={"detail": "令牌无效或已过期"})

    uid = payload["sub"]
    from src.common.cache import cache as user_cache
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
            user_cache.set(f"user_{uid}", None, ttl=1)
            return JSONResponse(status_code=401, content={"detail": "令牌版本不匹配"})
        if not user.get("is_active"):
            return JSONResponse(status_code=401, content={"detail": "用户不存在或已禁用"})

    request.state.user_id = uid
    request.state.user_token_version = payload.get("ver", 0)
    request.state.user = user

    return await call_next(request)
