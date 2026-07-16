"""一次性验证挑战：只存 HMAC，绑定用途和目标。"""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from tortoise import fields
from tortoise.models import Model


def hash_verification_code(code: str, purpose: str, target: str = "") -> str:
    from src.auth.jwt import SECRET_KEY

    message = f"{purpose}:{target.strip().lower()}:{code.strip()}".encode()
    return hmac.new(SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


class Captcha(Model):
    id = fields.UUIDField(pk=True)
    code_hash = fields.CharField(max_length=64)
    purpose = fields.CharField(max_length=32, default="captcha")
    target = fields.CharField(max_length=255, null=True)
    used = fields.BooleanField(default=False)
    attempts = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "captcha"
        schema = "public"
        indexes = (("purpose", "target", "created_at"),)

    @classmethod
    async def issue(cls, *, id: str, code: str, purpose: str = "captcha", target: str = ""):
        normalized_target = target.strip().lower()
        return await cls.create(
            id=id,
            code_hash=hash_verification_code(code, purpose, normalized_target),
            purpose=purpose,
            target=normalized_target or None,
        )

    def is_expired(self, ttl_minutes: int = 5) -> bool:
        return datetime.now(timezone.utc) - self.created_at > timedelta(minutes=ttl_minutes)
