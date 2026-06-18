"""
掌握度评测记录——每次用户自查掌握度一条记录
"""
from tortoise import fields
from tortoise.models import Model


class MasteryAttempt(Model):
    """用户掌握度自查评测记录"""

    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="mastery_attempts", on_delete=fields.CASCADE)
    topic = fields.ForeignKeyField("models.Topic", related_name="mastery_attempts", on_delete=fields.CASCADE)
    answer_text = fields.TextField()
    attempt_number = fields.IntField(default=1)

    # 五维分数（无 LLM，纯向量+字符串计算）
    score_keypoint = fields.FloatField(null=True)
    score_structure = fields.FloatField(null=True)
    score_keyword = fields.FloatField(null=True)
    score_length = fields.FloatField(null=True)
    score_coherence = fields.FloatField(null=True)
    score_total = fields.FloatField(null=True)

    is_mastered = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "mastery_attempt"
        schema = "public"
