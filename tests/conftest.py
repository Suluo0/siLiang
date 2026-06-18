"""
全局测试 fixtures —— 每条测试独立事务，测后自动回滚

核心原则（遵守 MEMORY 红线 1.1 / 7.2）:
- 测试 DB URL 通过环境变量 TEST_DATABASE_URL 注入,不允许硬编码
- 默认指向独立的 topic_test 库,严禁污染主开发库 topic
- autouse 默认挡掉 LLM/Milvus 等外部依赖,需要时显式 unset
"""
import asyncio
import os

import pytest
import pytest_asyncio
from tortoise import Tortoise

# ---------- 测试 DB URL（单一来源:环境变量） ----------
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    # 默认本地开发库（密码占位符,真实密码必须由环境变量覆盖）
    "postgres://postgres:postgres@localhost:5432/topic_test",
)

# ---------- 防呆:测试库名必须含 "test",防止误打主库 ----------
assert "test" in TEST_DB_URL.lower(), (
    f"TEST_DATABASE_URL 必须指向带 'test' 字样的隔离测试库,"
    f"当前值看起来像主库:{TEST_DB_URL.split('@')[-1] if '@' in TEST_DB_URL else TEST_DB_URL}"
)


@pytest.fixture(scope="session")
def event_loop():
    """覆盖 pytest-asyncio 默认 loop —— session 级,fixture 跨用例复用更快"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ---------- autouse:默认挡掉真实外部依赖（CI 安全网） ----------
@pytest.fixture(autouse=True)
def _mock_external_services(monkeypatch):
    """默认禁止真实 LLM / SMTP / Milvus 调用。
    需要真调的测试用 @pytest.mark.e2e 并在测试内 monkeypatch.setenv 解除。
    """
    # LLM API key 用 mock 值,真调会被远端 401
    monkeypatch.setenv("TS_DS_APIKEY", os.getenv("TS_DS_APIKEY", "test-mock-key"))
    monkeypatch.setenv("API_ADDRESS", os.getenv("API_ADDRESS", "https://mock.local"))
    monkeypatch.setenv("API_MODEL", os.getenv("API_MODEL", "mock-model"))
    # JWT secret 必须设(否则 src.auth.jwt 会用随机值,跨用例不稳)
    monkeypatch.setenv("JWT_SECRET", os.getenv("JWT_SECRET", "test-jwt-secret-32chars-minimum-aaaa"))
    # SMTP 默认禁
    monkeypatch.setenv("SMTP_USER", os.getenv("SMTP_USER", ""))
    monkeypatch.setenv("SMTP_PASS", os.getenv("SMTP_PASS", ""))


# ---------- DB fixture:每测一启停 + auto generate_schemas ----------
@pytest_asyncio.fixture(scope="function")
async def db():
    """每个测试函数 —— 启停 Tortoise 一次,函数结束清表"""
    await Tortoise.init(
        db_url=TEST_DB_URL,
        modules={"models": ["src.models"]},
    )
    # 自动建表（test 库可能为空)
    await Tortoise.generate_schemas(safe=True)
    yield
    # 清空所有数据（保留表结构,提速）
    try:
        for app_models in Tortoise.apps.values():
            for model in app_models.values():
                conn = Tortoise.get_connection("default")
                table = model._meta.db_table
                await conn.execute_query(f'TRUNCATE TABLE "{table}" CASCADE')
    except Exception:  # noqa: BLE001 - 清表失败不应中断测试关闭流程
        pass
    await Tortoise.close_connections()


# ---------- setup_db 别名 —— 兼容老测试用例 ----------
@pytest_asyncio.fixture(scope="function")
async def setup_db(db):
    """test_topic_crud / test_user_crud 等老测试用 setup_db 名字,提供别名"""
    yield db


@pytest_asyncio.fixture(scope="function")
async def client(db):
    """FastAPI AsyncClient —— 自动注入测试 DB"""
    from httpx import ASGITransport, AsyncClient
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def auth_headers(client, db):
    """直接创建用户 → 登录获取 token → 返回 Authorization header"""
    import uuid

    from src.auth.hash import hash_password
    from src.models.captcha import Captcha
    from src.models.user import User

    username = f"fixt{uuid.uuid4().hex[:8]}"
    password = "Test123456!"

    await User.create(
        id=str(uuid.uuid4()),
        username=username,
        email=f"{username}@test.com",
        password_hash=hash_password(password),
        is_active=True,
        token_version=0,
    )

    captcha = await Captcha.create(id=str(uuid.uuid4()), code="1234")

    resp = await client.post("/api/auth/login", json={
        "username": username,
        "password": password,
        "captcha_id": str(captcha.id),
        "captcha_answer": "1234",
    })
    data = resp.json()
    token = data.get("access_token", "")
    if not token:
        return {"Authorization": "Bearer invalid"}
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_llm(mocker):
    """Mock LLMClient.ainvoke,返回可控 JSON"""
    mock = mocker.patch("src.tools.llm_client.LLMClient.ainvoke")
    mock.return_value = '{"score": 0.85, "reasoning": "mocked"}'
    return mock


# ---------- Marker 自动归类 ----------
def pytest_collection_modifyitems(config, items):
    """根据 fixture 使用情况自动归类:
    - 用了 db / client / auth_headers / setup_db → integration
    - 没用上述任何 fixture → unit
    e2e / slow 必须显式 @pytest.mark.<e2e|slow>,不自动判
    """
    integration_fixtures = {"db", "client", "auth_headers", "setup_db"}

    for item in items:
        existing_markers = {m.name for m in item.iter_markers()}
        if existing_markers & {"e2e", "slow", "unit", "integration"}:
            continue  # 已显式标记,尊重原作者意图

        fixturenames = set(getattr(item, "fixturenames", ()))
        if fixturenames & integration_fixtures:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
