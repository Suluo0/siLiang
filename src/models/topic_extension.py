"""扩展延伸知识点"""
from tortoise import fields
from tortoise.models import Model


class TopicExtension(Model):
    """扩展延伸关联"""

    id = fields.UUIDField(pk=True)
    topic = fields.ForeignKeyField(
        "models.Topic", related_name="extensions", on_delete=fields.CASCADE
    )
    knowledge = fields.ForeignKeyField(
        "models.KnowledgeDict", related_name="extension_of", on_delete=fields.CASCADE
    )
    importance = fields.IntField(default=3)
    sort_order = fields.IntField(default=0)

    class Meta:
        table = "topic_extension"
        schema = "public"
        unique_together = (("topic_id", "knowledge_id"),)

    def __str__(self):
        return f"TopicExtension(topic={self.topic_id}, knowledge={self.knowledge_id})"
