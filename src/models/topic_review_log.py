from tortoise import fields
from tortoise.models import Model


class TopicReviewLog(Model):
    """复习记录"""

    id = fields.UUIDField(pk=True)
    topic = fields.ForeignKeyField(
        "models.Topic", related_name="review_logs", on_delete=fields.CASCADE
    )
    review_date = fields.DatetimeField(null=True)
    mastery_level = fields.IntField(null=True)
    review_duration = fields.IntField(null=True)
    notes = fields.TextField(null=True)

    class Meta:
        table = "topic_review_log"
        schema = "public"

    def __str__(self):
        return f"TopicReviewLog({self.id})"
