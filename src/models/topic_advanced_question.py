from tortoise import fields
from tortoise.models import Model


class TopicAdvancedQuestion(Model):
    """进阶问题"""

    id = fields.UUIDField(pk=True)
    topic = fields.ForeignKeyField(
        "models.Topic", related_name="advanced_questions", on_delete=fields.CASCADE
    )
    question = fields.TextField()
    answer_hint = fields.TextField(null=True)
    sort_order = fields.IntField(default=0)

    class Meta:
        table = "topic_advanced_question"
        schema = "public"

    def __str__(self):
        return f"TopicAdvancedQuestion({self.id})"
