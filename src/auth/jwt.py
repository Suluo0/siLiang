"""
JWT Token 管理 —— 签发 / 验证 / 过期
Access Token: 15min, 放在 Authorization header
Refresh Token: 7d, 用于续期
"""
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

SECRET_KEY = "topicsystem-jwt-secret-change-in-production-2026"
ALGORITHM = "HS256"
ACCESS_EXPIRE_MINUTES = 15
REFRESH_EXPIRE_DAYS = 7


def create_access_token(user_id: str, token_version: int) -> str:
    payload = {
        "sub": user_id,
        "ver": token_version,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str, token_version: int) -> str:
    payload = {
        "sub": user_id,
        "ver": token_version,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    """解码 token，失败返回 None"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def create_tokens(user_id: str, token_version: int) -> dict:
    """签发 access + refresh token pair"""
    return {
        "access_token": create_access_token(user_id, token_version),
        "refresh_token": create_refresh_token(user_id, token_version),
        "token_type": "bearer",
        "expires_in": ACCESS_EXPIRE_MINUTES * 60,
    }
