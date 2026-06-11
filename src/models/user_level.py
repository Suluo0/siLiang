from tortoise import fields
from tortoise.models import Model


class UserLevel(Model):
    """UserLevel 模型"""


    id = fields.UUIDField(pk=True)

    level_name = fields.CharField(max_length=50)

    level_code = fields.IntField()

    experience_min = fields.IntField()

    experience_max = fields.IntField(null=True)

    privileges = fields.TextField(null=True)

    created_at = fields.DatetimeField(null=True, auto_now_add=True)

    updated_at = fields.DatetimeField(null=True, auto_now_add=True)




    class Meta:
        table = "user_level"
        schema = "public"

    def __str__(self):
        return f"UserLevel({self.id})"