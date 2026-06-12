"""
面试总结 - 一轮面试结束后的报告
"""
from tortoise import fields
from tortoise.models import Model


class InterviewSummary(Model):
    """面试总结报告"""

    id = fields.UUIDField(pk=True)
    room = fields.OneToOneField("models.InterviewRoom", related_name="summary", on_delete=fields.CASCADE)

    overall_score = fields.FloatField()
    level_estimate = fields.CharField(max_length=20)  # 初级 / 中级 / 高级 / 专家

    accuracy_avg = fields.FloatField()
    depth_avg = fields.FloatField()
    completeness_avg = fields.FloatField()
    clarity_avg = fields.FloatField()
    practical_avg = fields.FloatField()

    strengths = fields.JSONField(default=[])
    weaknesses = fields.JSONField(default=[])
    recommendations = fields.JSONField(default=[])

    raw_report = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "interview_summary"
        schema = "public"
