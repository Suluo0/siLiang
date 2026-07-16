"""
Outbox 补偿任务表模型
"""
from tortoise import fields
from tortoise.models import Model


class Outbox(Model):
    """Outbox 补偿表 — PG 成功但 Milvus 写入失败时记录"""
    id = fields.UUIDField(pk=True)
    event_type = fields.CharField(max_length=64)        # TOPIC_CREATED
    payload = fields.JSONField()                        # {"topic_id": "...", "core_concept": "..."}
    status = fields.CharField(max_length=16, default="PENDING")
    retry_count = fields.IntField(default=0)
    error_message = fields.TextField(null=True)
    next_retry_at = fields.DatetimeField(null=True)
    lease_until = fields.DatetimeField(null=True)
    worker_id = fields.CharField(max_length=64, null=True)
    idempotency_key = fields.CharField(max_length=128, null=True, unique=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    processed_at = fields.DatetimeField(null=True)

    class Meta:
        table = "outbox"
        indexes = (("status", "next_retry_at"), ("status", "lease_until"))
