"""
JWT Token 管理 —— 签发 / 验证 / 过期
Access Token: 15min, 放在 Authorization header
Refresh Token: 7d, 用于续期
"""
import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    import secrets
    import warnings
    SECRET_KEY = secrets.token_urlsafe(32)
    warnings.warn("JWT_SECRET not set in environment, using a temporary random key. "
                  "Set JWT_SECRET in .env for production!")

ALGORITHM = "HS256"
ACCESS_EXPIRE_MINUTES = 10080  # 7 days
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
