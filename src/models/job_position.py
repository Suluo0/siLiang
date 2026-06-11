"""
目标岗位表
"""
from tortoise import fields
from tortoise.models import Model


class JobPosition(Model):
    """岗位"""

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50)
    category = fields.CharField(max_length=30, null=True)  # 前端/后端/全栈/数据/测试/运维
    sort_order = fields.IntField(default=0)

    class Meta:
        table = "job_position"
        schema = "public"
