"""
User 模型 CRUD 测试
测试通过标准：每张表都包含一条测试数据
"""

import pytest
from src.models import User, UserProfile, UserTopicProgress, Topic


@pytest.mark.asyncio
async def test_user_crud(setup_db):
    """测试 User 主表 CRUD"""
    # Create
    user = await User.create(
        username="testuser",
        email="test@example.com",
        password_hash="hashed_password",
        is_active=True,
        is_superuser=False,
    )
    assert user.id is not None
    assert user.username == "testuser"
    assert user.email == "test@example.com"

    # Read
    fetched = await User.filter(id=user.id).first()
    assert fetched is not None
    assert fetched.username == "testuser"

    # Update
    fetched.is_superuser = True
    await fetched.save()
    updated = await User.filter(id=user.id).first()
    assert updated.is_superuser is True

    print(f"✅ User CRUD 测试通过: {user.id}")


@pytest.mark.asyncio
async def test_user_profile(setup_db):
    """测试用户信息表（一对一）"""
    user = await User.create(
        username="testuser2", email="test2@example.com", password_hash="xxx"
    )
    profile = await UserProfile.create(
        user=user, nickname="测试用户", bio="这是一段个人简介"
    )
    assert profile.id is not None
    assert profile.nickname == "测试用户"

    # 验证一对一关系
    await user.fetch_related("profile")
    assert user.profile is not None
    assert user.profile.nickname == "测试用户"

    print(f"✅ UserProfile 测试通过: {profile.id}")


@pytest.mark.asyncio
async def test_user_topic_progress(setup_db):
    """测试用户话题进度表"""
    user = await User.create(
        username="testuser3", email="test3@example.com", password_hash="xxx"
    )
    topic = await Topic.create(topic="HashMap", domain="Java基础")

    progress = await UserTopicProgress.create(
        user=user,
        topic=topic,
        mastery_level=75,
        review_count=3,
        notes="第三轮复习完成",
    )
    assert progress.id is not None
    assert progress.mastery_level == 75
    assert progress.review_count == 3

    print(f"✅ UserTopicProgress 测试通过: {progress.id}")
