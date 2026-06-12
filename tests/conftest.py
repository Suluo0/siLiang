import pytest
import pytest_asyncio
from src.config.database import init_db, close_db


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
    await init_db()
    yield
    await close_db()
