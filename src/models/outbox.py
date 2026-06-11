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
    status = fields.CharField(max_length=16, default="PENDING")  # PENDING / PROCESSED / FAILED
    retry_count = fields.IntField(default=0)
    error_message = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    processed_at = fields.DatetimeField(null=True)

    class Meta:
        table = "outbox"
