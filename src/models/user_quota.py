"""
用户配额模型 —— 注册后 20 次题目 + 5 次 Agent 对话
"""
from tortoise import fields
from tortoise.models import Model


class UserQuota(Model):
    """每位用户的使用配额"""

    id = fields.UUIDField(pk=True)
    user = fields.OneToOneField("models.User", related_name="quota", on_delete=fields.CASCADE)

    topic_credits = fields.IntField(default=20, description="面试题访问剩余次数")
    agent_credits = fields.IntField(default=5, description="Agent 对话剩余次数")

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_quota"
        schema = "public"

    def __str__(self):
        return f"UserQuota(user={self.user_id}, topic={self.topic_credits}, agent={self.agent_credits})"
