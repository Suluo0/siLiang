"""
知识点别名 —— 同义知识点映射
例如："红黑树结构" → alias → "红黑树"
防止 Agent 将同一概念输出为不同名称
"""
from tortoise import fields
from tortoise.models import Model


class KnowledgeAlias(Model):
    """知识点别名"""

    id = fields.UUIDField(pk=True)
    knowledge = fields.ForeignKeyField(
        "models.KnowledgeDict", related_name="aliases", on_delete=fields.CASCADE
    )
    alias = fields.CharField(max_length=255)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "knowledge_alias"
        schema = "public"
        unique_together = (("knowledge_id", "alias"),)

    def __str__(self):
        return f"KnowledgeAlias({self.alias} → {self.knowledge_id})"
