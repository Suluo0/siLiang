"""
用户-题目状态中间表
标记: mastered / learning / none
"""
from tortoise import fields
from tortoise.models import Model


class UserTopicStatus(Model):
    """用户对题目的掌握状态"""

    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="topic_statuses", on_delete=fields.CASCADE)
    topic = fields.ForeignKeyField("models.Topic", related_name="user_statuses", on_delete=fields.CASCADE)
    status = fields.CharField(max_length=20, default="learning")  # mastered / learning

    # 面试维度
    interview_proficiency = fields.FloatField(default=0.0)         # 面试场景熟练度 0-100
    last_interview_score = fields.FloatField(null=True)            # 最近面试得分
    interview_count = fields.IntField(default=0)                   # 被问及次数
    interview_weak_points = fields.JSONField(default=[])           # 面试暴露的弱点

    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_topic_status"
        schema = "public"
        unique_together = (("user", "topic"),)
