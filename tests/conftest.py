import pytest
import pytest_asyncio
from tortoise import Tortoise, connections


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环供所有测试使用"""
    import asyncio
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def setup_db():
    """每个测试函数前后初始化数据库"""
    # 使用项目的实际 PostgreSQL 数据库
    db_url = "postgres://postgres:Xswl1139@localhost:5432/topic"
    await Tortoise.init(
        db_url=db_url,
        modules={"models": ["src.models"]},
    )
    yield
    await Tortoise.close_connections()
