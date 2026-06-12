"""评估基准 —— 各级面试题和标准答案"""
from tortoise import fields
from tortoise.models import Model


class TopicEvaluationAnchor(Model):
    """评估基准"""

    id = fields.UUIDField(pk=True)
    topic = fields.ForeignKeyField(
        "models.Topic", related_name="evaluation_anchors", on_delete=fields.CASCADE
    )
    level = fields.CharField(max_length=50, null=True)
    question = fields.TextField()
    expected_answer = fields.TextField(null=True)
    sort_order = fields.IntField(default=0)

    class Meta:
        table = "topic_evaluation_anchor"
        schema = "public"

    def __str__(self):
        return f"TopicEvaluationAnchor({self.id})"
