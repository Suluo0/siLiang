"""
UserLevel 模型 CRUD 测试
"""

import pytest
from src.models import UserLevel


@pytest.mark.asyncio
async def test_user_level_crud(setup_db):
    """测试 UserLevel CRUD"""
    # Create
    level = await UserLevel.create(
        level_name="初学者",
        level_code=1,
        experience_min=0,
        experience_max=100,
        privileges="基础功能",
    )
    assert level.id is not None
    assert level.level_name == "初学者"
    assert level.level_code == 1

    # Read
    fetched = await UserLevel.filter(id=level.id).first()
    assert fetched is not None
    assert fetched.level_name == "初学者"

    # Update
    fetched.level_code = 2
    await fetched.save()
    updated = await UserLevel.filter(id=level.id).first()
    assert updated.level_code == 2

    print(f"✅ UserLevel CRUD 测试通过: {level.id}")
