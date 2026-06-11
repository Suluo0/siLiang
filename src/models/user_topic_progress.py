from tortoise import fields
from tortoise.models import Model


class UserTopicProgress(Model):
    """用户话题进度表"""

    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField(
        "models.User", related_name="topic_progress", on_delete=fields.CASCADE
    )
    topic = fields.ForeignKeyField(
        "models.Topic", related_name="user_progress", on_delete=fields.CASCADE
    )
    mastery_level = fields.IntField(default=0)
    review_count = fields.IntField(default=0)
    last_reviewed = fields.DatetimeField(null=True)
    next_review = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_topic_progress"
        schema = "public"
        # 复合唯一约束：同一用户对同一话题只能有一条进度记录
        unique_together = (("user", "topic"),)

    def __str__(self):
        return f"UserTopicProgress({self.id}, user={self.user_id}, topic={self.topic_id})"
