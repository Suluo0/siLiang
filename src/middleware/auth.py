"""认证中间件：公开路由显式放行，其余路由默认拒绝。"""
from fastapi import Request
from fastapi.responses import JSONResponse

from src.auth.deps import is_public_request


async def auth_middleware(request: Request, call_next):
    path = request.url.path.rstrip("/") or "/"
    if is_public_request(request.method, path):
        if request.method == "GET" and path.startswith("/api/topic/"):
            request.state.quota_exhausted = True
        return await call_next(request)

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or not auth[7:].strip():
        return JSONResponse(status_code=401, content={"detail": "未提供认证令牌"})

    from src.auth.jwt import decode_token
    from src.models.user import User

    payload = decode_token(auth[7:].strip(), expected_type="access")
    if not payload:
        return JSONResponse(status_code=401, content={"detail": "令牌无效或已过期"})

    user = await User.filter(id=payload["sub"], is_active=True).first()
    if not user or user.token_version != payload["ver"]:
        return JSONResponse(status_code=401, content={"detail": "用户或令牌已失效"})

    request.state.user_id = str(user.id)
    request.state.user_token_version = user.token_version
    request.state.user = user
    return await call_next(request)
