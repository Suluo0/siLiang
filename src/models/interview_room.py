"""
面试房间 - 一次模拟面试的会话容器
"""
from tortoise import fields
from tortoise.models import Model


class InterviewRoom(Model):
    """面试会话"""

    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="interviews", on_delete=fields.CASCADE)
    title = fields.CharField(max_length=200, default="模拟面试")
    status = fields.CharField(max_length=20, default="active")  # active / ended / cancelled

    persona_id = fields.CharField(max_length=64)
    target_position = fields.CharField(max_length=100)
    jd_text = fields.TextField(null=True)
    resume_text = fields.TextField(null=True)

    jd_analysis = fields.JSONField(null=True)
    resume_analysis = fields.JSONField(null=True)
    match_gap = fields.JSONField(null=True)

    total_rounds = fields.IntField(default=0)
    avg_score = fields.FloatField(default=0.0)
    weakness_areas = fields.JSONField(default=[])

    created_at = fields.DatetimeField(auto_now_add=True)
    ended_at = fields.DatetimeField(null=True)

    rounds: fields.ReverseRelation["InterviewRound"]

    class Meta:
        table = "interview_room"
        schema = "public"
