"""
测试数据工厂 —— 一行创建带默认值的数据库记录
"""
import uuid


async def create_test_user(username="tester", email="tester@test.com", password="Test123456"):
    """注册用户并返回 (user_dict, access_token)"""
    from src.models.user import User
    from src.auth.hash import hash_password

    user = await User.create(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        password_hash=hash_password(password),
        is_active=True,
        token_version=0,
    )
    return user


async def create_test_topic(topic="测试题目", domain="测试领域", **overrides):
    """创建一道测试题目"""
    from src.models import Topic

    defaults = {
        "id": str(uuid.uuid4()),
        "topic": topic,
        "domain": domain,
        "difficulty": 3,
        "mastery_level": 0,
        "tags": ["tag1", "tag2"],
        "keywords": ["kw1", "kw2"],
        "one_liner": f"{topic}的简要概述",
        "core_summary": f"{topic}的核心总结内容",
        "core_points": "要点1\n要点2\n要点3",
        "detailed_explanation": f"{topic}的详细解释，包含丰富的技术细节和实现方式。",
        "code_example": "System.out.println(\"hello\");",
        "traps": "常见陷阱：忘关流",
        "bonuses": "加分点：了解源码",
    }
    defaults.update(overrides)

    t = await Topic.create(**defaults)
    return t


async def create_test_quota(user_id: str, agent_credits: int = 5, topic_credits: int = 20):
    """创建用户配额"""
    from src.models.user_quota import UserQuota
    return await UserQuota.create(id=str(uuid.uuid4()), user_id=user_id,
                                  agent_credits=agent_credits, topic_credits=topic_credits)
