from tortoise import fields
from tortoise.models import Model


class TopicCoreConcept(Model):
    """核心概念"""

    id = fields.UUIDField(pk=True)
    topic = fields.ForeignKeyField(
        "models.Topic", related_name="core_concepts", on_delete=fields.CASCADE
    )
    content = fields.TextField()
    sort_order = fields.IntField(default=0)

    class Meta:
        table = "topic_core_concept"
        schema = "public"

    def __str__(self):
        return f"TopicCoreConcept({self.id})"
