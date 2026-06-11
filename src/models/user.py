from tortoise import fields
from tortoise.models import Model


class User(Model):
    """用户基础表"""

    id = fields.UUIDField(pk=True)
    username = fields.CharField(max_length=50, unique=True)
    email = fields.CharField(max_length=100, unique=True)
    password_hash = fields.CharField(max_length=255)
    is_active = fields.BooleanField(default=True)
    is_superuser = fields.BooleanField(default=False)

    # Auth
    token_version = fields.IntField(default=0)
    email_verified = fields.BooleanField(default=False)
    verification_token = fields.CharField(max_length=64, null=True)
    last_login = fields.DatetimeField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 一对一关系
    profile: fields.OneToOneRelation["UserProfile"]
    # 一对多关系
    topic_progress: fields.ReverseRelation["UserTopicProgress"]

    class Meta:
        table = "user"
        schema = "public"

    def __str__(self):
        return f"User({self.id}, {self.username})"
