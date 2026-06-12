"""
知识点词典 —— 所有题目共享的知识点名称池
同义知识点通过 knowledge_alias 表关联
"""
from tortoise import fields
from tortoise.models import Model


class KnowledgeDict(Model):
    """知识点名称词典"""

    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255, unique=True)
    description = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "knowledge_dict"
        schema = "public"

    def __str__(self):
        return f"KnowledgeDict({self.name})"
