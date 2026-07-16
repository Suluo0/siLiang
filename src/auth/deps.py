"""
鉴权依赖 —— FastAPI Depends 方式
全局 Middleware + 公开路由白名单
"""
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.auth.jwt import decode_token
from src.models.user import User

security = HTTPBearer(auto_error=False)

# 不需要鉴权的公开路径（单一来源，main.py 也引用此列表）
PUBLIC_PATHS = {
    "/", "/ping", "/docs", "/openapi.json", "/redoc",
    "/api/auth/register", "/api/auth/login", "/api/auth/refresh",
    "/api/auth/captcha", "/api/auth/send-code",
    "/api/topic/tags", "/api/topic/positions", "/api/topic/list",
    "/api/interview/personas",
    "/terms", "/privacy",
}


def is_public_request(method: str, path: str) -> bool:
    """单一公开路由判定源；题目详情 GET 允许匿名预览，但由 API 截断付费内容。"""
    normalized = path.rstrip("/") or "/"
    if normalized in PUBLIC_PATHS:
        return True
    parts = normalized.split("/")
    return method.upper() == "GET" and len(parts) == 4 and parts[1:3] == ["api", "topic"]


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User | None:
    """从 Authorization header 提取当前用户。公开路径返回 None。"""
    path = request.url.path.rstrip("/")

    # 公开路径跳过鉴权
    if is_public_request(request.method, path):
        return None

    if not credentials:
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    payload = decode_token(credentials.credentials, expected_type="access")
    if not payload:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")

    user = await User.filter(id=payload["sub"], is_active=True).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    if user.token_version != payload.get("ver", 0):
        raise HTTPException(status_code=401, detail="令牌版本不匹配（密码已修改，请重新登录）")

    return user


async def get_current_active_user(
    user: User | None = Depends(get_current_user),
) -> User:
    """强制要求登录——公开路径不可调用"""
    if user is None:
        raise HTTPException(status_code=401, detail="需要登录")
    return user
