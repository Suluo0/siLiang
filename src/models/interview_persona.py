"""
面试官人设配置
"""
from tortoise import fields
from tortoise.models import Model


class InterviewPersona(Model):
    """预设面试官人设"""

    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=100)
    description = fields.TextField()
    tags = fields.JSONField(default=[])

    personality = fields.CharField(max_length=50)          # friendly, neutral, strict, pressure
    technical_depth = fields.IntField(default=3)           # 1-5
    communication_style = fields.CharField(max_length=50)  # 引导式, 追问式, 压力式
    difficulty_bias = fields.FloatField(default=0.0)       # -1.0 ~ +1.0

    system_prompt = fields.TextField()
    opening_line = fields.TextField()
    follow_up_templates = fields.JSONField(default=[])

    is_default = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "interview_persona"
        schema = "public"
