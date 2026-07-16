"""R-003 JWT 类型、形状和寿命安全测试。"""
from datetime import datetime, timezone

import pytest

from src.auth.jwt import (
    ACCESS_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
    decode_token,
    _resolve_secret,
)

pytestmark = [pytest.mark.unit, pytest.mark.security]


def test_access_token_is_short_lived():
    token = create_access_token("user-1", 3)
    payload = decode_token(token, expected_type="access")
    assert payload is not None
    lifetime = payload["exp"] - int(datetime.now(timezone.utc).timestamp())
    assert ACCESS_EXPIRE_MINUTES == 15
    assert 0 < lifetime <= 15 * 60


def test_refresh_cannot_be_used_as_access():
    token = create_refresh_token("user-1", 3)
    assert decode_token(token, expected_type="access") is None
    assert decode_token(token, expected_type="refresh") is not None


def test_access_cannot_be_used_as_refresh():
    token = create_access_token("user-1", 3)
    assert decode_token(token, expected_type="refresh") is None


@pytest.mark.parametrize("secret", [None, "", "change-me-in-production", "too-short"])
def test_production_rejects_missing_or_placeholder_secret(secret):
    with pytest.raises(RuntimeError):
        _resolve_secret(secret, "production")


def test_production_accepts_strong_secret():
    secret = "a-production-secret-with-at-least-32-characters"
    assert _resolve_secret(secret, "production") == secret


@pytest.mark.parametrize("token_type", [None, "", "admin"])
def test_unknown_token_type_rejected(token_type, monkeypatch):
    from jose import jwt
    from src.auth import jwt as jwt_module

    payload = {"sub": "user-1", "ver": 0, "type": token_type, "exp": 4_102_444_800}
    token = jwt.encode(payload, jwt_module.SECRET_KEY, algorithm=jwt_module.ALGORITHM)
    assert decode_token(token) is None
