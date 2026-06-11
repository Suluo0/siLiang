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
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_topic_status"
        schema = "public"
        unique_together = (("user", "topic"),)
