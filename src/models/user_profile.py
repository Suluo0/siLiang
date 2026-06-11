from tortoise import fields
from tortoise.models import Model


class UserProfile(Model):
    """用户信息表（一对一）"""

    id = fields.UUIDField(pk=True)
    user = fields.OneToOneField(
        "models.User", related_name="profile", on_delete=fields.CASCADE
    )
    nickname = fields.CharField(max_length=50, null=True)
    avatar = fields.CharField(max_length=255, null=True)
    bio = fields.TextField(null=True)

    class Meta:
        table = "user_profile"
        schema = "public"

    def __str__(self):
        return f"UserProfile({self.id}, user_id={self.user_id})"
