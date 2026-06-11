from tortoise import fields
from tortoise.models import Model


class TopicReference(Model):
    """参考资源"""

    id = fields.UUIDField(pk=True)
    topic = fields.ForeignKeyField(
        "models.Topic", related_name="references", on_delete=fields.CASCADE
    )
    title = fields.CharField(max_length=255, null=True)
    url = fields.TextField(null=True)
    description = fields.TextField(null=True)
    sort_order = fields.IntField(default=0)

    class Meta:
        table = "topic_reference"
        schema = "public"

    def __str__(self):
        return f"TopicReference({self.id})"
