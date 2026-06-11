from tortoise import fields
from tortoise.models import Model


class TopicSimilarQuestion(Model):
    """相似问题"""

    id = fields.UUIDField(pk=True)
    topic = fields.ForeignKeyField(
        "models.Topic", related_name="similar_questions", on_delete=fields.CASCADE
    )
    question = fields.TextField()
    answer_hint = fields.TextField(null=True)
    sort_order = fields.IntField(default=0)

    class Meta:
        table = "topic_similar_question"
        schema = "public"

    def __str__(self):
        return f"TopicSimilarQuestion({self.id})"
