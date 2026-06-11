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

    # 会员 / 偏好
    membership_level = fields.CharField(max_length=20, default="free")
    target_position = fields.CharField(max_length=100, null=True)
    learning_preference = fields.CharField(max_length=50, null=True)
    experience_level = fields.CharField(max_length=20, null=True)
    today_target = fields.IntField(default=0)
    preferences_filled = fields.BooleanField(default=False)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    profile: fields.OneToOneRelation["UserProfile"]
    topic_statuses: fields.ReverseRelation["UserTopicStatus"]

    class Meta:
        table = "user"
        schema = "public"

    def __str__(self):
        return f"User({self.id}, {self.username})"
