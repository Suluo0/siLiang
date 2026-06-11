from tortoise import fields
from tortoise.models import Model


class TopicDerivative(Model):
    """衍生知识"""

    id = fields.UUIDField(pk=True)
    topic = fields.ForeignKeyField(
        "models.Topic", related_name="derivatives", on_delete=fields.CASCADE
    )
    content = fields.TextField()
    sort_order = fields.IntField(default=0)

    class Meta:
        table = "topic_derivative"
        schema = "public"

    def __str__(self):
        return f"TopicDerivative({self.id})"
