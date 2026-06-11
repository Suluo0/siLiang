"""
CAPTCHA 验证码模型 — 4 位数字，5 分钟有效
"""
from tortoise import fields
from tortoise.models import Model


class Captcha(Model):
    """图形验证码"""

    id = fields.UUIDField(pk=True)
    code = fields.CharField(max_length=8, description="4位验证码")

    used = fields.BooleanField(default=False, description="是否已被使用")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "captcha"
        schema = "public"

    def is_expired(self) -> bool:
        from datetime import datetime, timezone, timedelta
        return datetime.now(timezone.utc) - self.created_at > timedelta(minutes=5)
