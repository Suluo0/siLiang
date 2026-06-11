from tortoise import fields
from tortoise.models import Model


class TopicPrerequisite(Model):
    """前置知识"""

    id = fields.UUIDField(pk=True)
    topic = fields.ForeignKeyField(
        "models.Topic", related_name="prerequisites", on_delete=fields.CASCADE
    )
    content = fields.TextField()
    sort_order = fields.IntField(default=0)

    class Meta:
        table = "topic_prerequisite"
        schema = "public"

    def __str__(self):
        return f"TopicPrerequisite({self.id})"
