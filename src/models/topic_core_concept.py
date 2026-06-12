"""核心概念知识点"""
from tortoise import fields
from tortoise.models import Model


class TopicCoreConcept(Model):
    """核心概念关联"""

    id = fields.UUIDField(pk=True)
    topic = fields.ForeignKeyField(
        "models.Topic", related_name="core_concepts", on_delete=fields.CASCADE
    )
    knowledge = fields.ForeignKeyField(
        "models.KnowledgeDict", related_name="core_concept_of", on_delete=fields.CASCADE
    )
    importance = fields.IntField(default=3)
    sort_order = fields.IntField(default=0)

    class Meta:
        table = "topic_core_concept"
        schema = "public"
        unique_together = (("topic_id", "knowledge_id"),)

    def __str__(self):
        return f"TopicCoreConcept(topic={self.topic_id}, knowledge={self.knowledge_id})"
