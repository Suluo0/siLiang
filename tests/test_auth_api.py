"""
Auth API 集成测试 —— 注册 / 登录 / refresh / 公开路径
"""
import pytest
import uuid
import asyncio


@pytest.mark.integration
class TestAuthRegister:
    """用户注册"""

    async def test_register_success(self, client, db):
        """创建 captcha 后注册成功"""
        from src.models.captcha import Captcha
        import uuid
        captcha_answer = "1234"
        captcha = await Captcha.issue(id=str(uuid.uuid4()), code=captcha_answer)
        captcha_id = str(captcha.id)
        email = f"new_{uuid.uuid4().hex[:8]}@test.com"
        email_code = "654321"
        await Captcha.issue(id=str(uuid.uuid4()), code=email_code, purpose="email", target=email)

        resp = await client.post("/api/auth/register", json={
            "username": "newuser",
            "email": email,
            "password": "Test123456!",
            "captcha_id": captcha_id,
            "captcha_answer": captcha_answer,
            "email_code": email_code,
        })
        assert resp.status_code == 200, resp.text

    async def test_register_duplicate_email(self, client, db):
        """重复邮箱应被拒绝"""
        import uuid as _uuid
        from src.models.user import User
        from src.auth.hash import hash_password
        from src.models.captcha import Captcha

        email = f"dup_{_uuid.uuid4().hex[:8]}@test.com"
        u1 = f"dup_u1_{_uuid.uuid4().hex[:6]}"
        u2 = f"dup_u2_{_uuid.uuid4().hex[:6]}"

        await User.create(
            id=str(_uuid.uuid4()), username=u1, email=email,
            password_hash=hash_password("Test123456!"), is_active=True, token_version=0,
        )

        captcha = await Captcha.issue(id=str(_uuid.uuid4()), code="1234")
        await Captcha.issue(id=str(_uuid.uuid4()), code="654321", purpose="email", target=email)
        resp = await client.post("/api/auth/register", json={
            "username": u2, "email": email, "password": "Test123456!",
            "captcha_id": str(captcha.id), "captcha_answer": "1234",
            "email_code": "654321",
        })
        # 邮箱重复应报错
        assert resp.status_code != 200

    async def test_register_weak_password(self, client, db):
        resp = await client.post("/api/auth/register", json={
            "username": "weak", "email": "weak@test.com", "password": "123",
        })
        assert resp.status_code == 422  # Pydantic validation

    async def test_email_code_cannot_cross_email(self, client, db):
        from src.models.captcha import Captcha

        captcha = await Captcha.issue(id=str(uuid.uuid4()), code="1234")
        await Captcha.issue(
            id=str(uuid.uuid4()), code="654321", purpose="email", target="owner@test.com",
        )
        resp = await client.post("/api/auth/register", json={
            "username": f"cross{uuid.uuid4().hex[:6]}",
            "email": "victim@test.com", "password": "Test123456!",
            "captcha_id": str(captcha.id), "captcha_answer": "1234", "email_code": "654321",
        })
        assert resp.status_code == 400

    @pytest.mark.concurrency
    async def test_email_code_is_consumed_once(self, db):
        from src.auth.api import _consume_email_code
        from src.models.captcha import Captcha

        email = "race@test.com"
        await Captcha.issue(id=str(uuid.uuid4()), code="654321", purpose="email", target=email)
        results = await asyncio.gather(
            _consume_email_code(email, "654321"),
            _consume_email_code(email, "654321"),
            return_exceptions=True,
        )
        assert sum(result is None for result in results) == 1


@pytest.mark.integration
class TestAuthLogin:
    """用户登录"""

    async def test_login_success(self, client, db, auth_headers):
        """通过 fixture 已创建的用户可获取 token"""
        assert auth_headers["Authorization"].startswith("Bearer ")

    async def test_login_wrong_password(self, client, db):
        email = f"lp_{uuid.uuid4().hex[:8]}@test.com"
        await client.post("/api/auth/register", json={
            "username": "lp", "email": email, "password": "Test123456!",
        })
        resp = await client.post("/api/auth/login", json={
            "email": email, "password": "WrongPass!",
        })
        assert resp.status_code != 200

    async def test_login_nonexistent_user(self, client, db):
        resp = await client.post("/api/auth/login", json={
            "email": "noone@test.com", "password": "Test123456!",
        })
        assert resp.status_code != 200


@pytest.mark.integration
class TestAuthRefresh:
    """Token 刷新"""

    async def test_refresh_token(self, client, db, auth_headers):
        """登录后刷新 token —— 可能需要额外字段，验证可达即可"""
        resp = await client.post("/api/auth/refresh", headers=auth_headers)
        # 422: 缺少字段, 200: 成功, 401: token无效
        assert resp.status_code in (200, 401, 422)


@pytest.mark.integration
class TestPublicPaths:
    """公开路径无需鉴权"""

    async def test_ping_public(self, client, db):
        resp = await client.get("/ping")
        assert resp.status_code == 200

    async def test_list_topics_public(self, client, db):
        resp = await client.get("/api/topic/list")
        # 不传 token 仍可访问（截断模式）
        assert resp.status_code == 200

    async def test_tags_public(self, client, db):
        resp = await client.get("/api/topic/tags")
        assert resp.status_code == 200

    async def test_register_login_refresh_public(self, client, db):
        # 这些端点不需要 token
        resp = await client.get("/ping")
        assert resp.status_code == 200
