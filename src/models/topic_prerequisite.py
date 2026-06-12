"""前置知识点"""
from tortoise import fields
from tortoise.models import Model


class TopicPrerequisite(Model):
    """前置知识关联"""

    id = fields.UUIDField(pk=True)
    topic = fields.ForeignKeyField(
        "models.Topic", related_name="prerequisites", on_delete=fields.CASCADE
    )
    knowledge = fields.ForeignKeyField(
        "models.KnowledgeDict", related_name="prerequisite_of", on_delete=fields.CASCADE
    )
    importance = fields.IntField(default=3)
    sort_order = fields.IntField(default=0)

    class Meta:
        table = "topic_prerequisite"
        schema = "public"
        unique_together = (("topic_id", "knowledge_id"),)

    def __str__(self):
        return f"TopicPrerequisite(topic={self.topic_id}, knowledge={self.knowledge_id})"
