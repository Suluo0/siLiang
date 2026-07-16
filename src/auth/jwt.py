"""
JWT Token 管理 —— 签发 / 验证 / 过期
Access Token: 15min, 放在 Authorization header
Refresh Token: 7d, 用于续期
"""
import os
from datetime import datetime, timedelta, timezone
import jwt
from jwt import PyJWTError

SECRET_KEY = os.getenv("JWT_SECRET")


def _resolve_secret(secret: str | None, environment: str) -> str:
    normalized = (secret or "").strip()
    is_placeholder = any(marker in normalized.lower() for marker in ("change-me", "your-", "example"))
    if environment.lower() in {"production", "prod"}:
        if len(normalized) < 32 or is_placeholder:
            raise RuntimeError("production JWT_SECRET must be a non-placeholder value of at least 32 characters")
        return normalized
    if normalized:
        return normalized
    import secrets
    import warnings
    warnings.warn("JWT_SECRET not set in environment, using a temporary random key. "
                  "Set JWT_SECRET in .env for production!")
    return secrets.token_urlsafe(32)


SECRET_KEY = _resolve_secret(SECRET_KEY, os.getenv("ENVIRONMENT", "development"))

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


def decode_token(token: str, expected_type: str | None = None) -> dict | None:
    """解码并校验 token 基本形状与用途，失败返回 None。"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not isinstance(payload.get("sub"), str) or not payload["sub"]:
            return None
        if not isinstance(payload.get("ver"), int):
            return None
        token_type = payload.get("type")
        if token_type not in {"access", "refresh"}:
            return None
        if expected_type and token_type != expected_type:
            return None
        return payload
    except (PyJWTError, TypeError, ValueError):
        return None


def create_tokens(user_id: str, token_version: int) -> dict:
    """签发 access + refresh token pair"""
    return {
        "access_token": create_access_token(user_id, token_version),
        "refresh_token": create_refresh_token(user_id, token_version),
        "token_type": "bearer",
        "expires_in": ACCESS_EXPIRE_MINUTES * 60,
    }
