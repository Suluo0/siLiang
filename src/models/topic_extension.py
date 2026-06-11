from tortoise import fields
from tortoise.models import Model


class TopicExtension(Model):
    """扩展延伸"""

    id = fields.UUIDField(pk=True)
    topic = fields.ForeignKeyField(
        "models.Topic", related_name="extensions", on_delete=fields.CASCADE
    )
    content = fields.TextField()
    sort_order = fields.IntField(default=0)

    class Meta:
        table = "topic_extension"
        schema = "public"

    def __str__(self):
        return f"TopicExtension({self.id})"
