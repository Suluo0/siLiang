"""
面试轮次 - 单轮 Q&A + 评分 + 路由
"""
from tortoise import fields
from tortoise.models import Model


class InterviewRound(Model):
    """面试中的每一轮问答"""

    id = fields.UUIDField(pk=True)
    room = fields.ForeignKeyField("models.InterviewRoom", related_name="rounds", on_delete=fields.CASCADE)
    round_number = fields.IntField()

    # 题目
    topic = fields.ForeignKeyField("models.Topic", null=True, on_delete=fields.SET_NULL)
    question_text = fields.TextField()
    question_type = fields.CharField(max_length=20)  # initial / derivative / extension / prerequisite

    # 用户回答
    answer_text = fields.TextField(null=True)
    answer_started_at = fields.DatetimeField(null=True)
    answer_duration_seconds = fields.IntField(default=0)

    # 五维评分
    score_accuracy = fields.FloatField(null=True)
    score_depth = fields.FloatField(null=True)
    score_completeness = fields.FloatField(null=True)
    score_clarity = fields.FloatField(null=True)
    score_practical = fields.FloatField(null=True)
    score_total = fields.FloatField(null=True)
    score_reasoning = fields.TextField(null=True)
    score_label = fields.CharField(max_length=20, null=True)  # 优秀 / 良好 / 一般 / 较差
    missing_points = fields.JSONField(null=True)

    # 路由决策
    route_decision = fields.CharField(max_length=20, null=True)  # derivative / extension / prerequisite / summary
    route_next_topic_id = fields.UUIDField(null=True)

    # 上下文提取
    extracted_context = fields.JSONField(null=True)

    # MQ 状态
    mq_status = fields.CharField(max_length=16, default="pending")  # pending / published / failed

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "interview_round"
        schema = "public"
