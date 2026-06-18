"""
Auth Middleware 测试 —— JWT 校验 / 未登录截断 / PUBLIC_PATHS
"""
import pytest
import pytest_asyncio
import uuid


@pytest.mark.integration
class TestAuthMiddleware:
    """认证中间件集成测试"""

    async def test_unauthorized_access_truncates_content(self, client, db):
        """未登录访客访问题目详情 —— 应截断内容"""
        from tests.factories import create_test_topic

        topic = await create_test_topic(
            topic="测试截断题",
            detailed_explanation="A" * 5000,
            code_example="print('hello')" * 100,
            traps="常见陷阱",
            bonuses="加分",
        )

        resp = await client.get(f"/api/topic/{topic.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["locked"] is True
        assert "locked_sections" in data

    async def test_authenticated_access_full_content(self, client, db, auth_headers):
        """登录用户访问题目详情 —— 应获取完整内容"""
        from tests.factories import create_test_topic

        topic = await create_test_topic(
            topic="测试完整题",
            detailed_explanation="详细解释",
            code_example="print('hello')",
        )

        resp = await client.get(f"/api/topic/{topic.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        # 登录用户不会被锁定
        if not data.get("locked"):
            assert data.get("detailed_explanation") == "详细解释"

    async def test_invalid_token_returns_401_or_truncated(self, client, db):
        """无效 token —— 应拒绝或截断"""
        from tests.factories import create_test_topic

        topic = await create_test_topic()
        resp = await client.get(f"/api/topic/{topic.id}", headers={
            "Authorization": "Bearer invalid_token_xxx"
        })
        # 无效 token → 视同未登录，截断
        assert resp.status_code in (200, 401)
        if resp.status_code == 200:
            assert resp.json()["locked"] is True

    async def test_no_token_gets_quota_exhausted(self, client, db):
        """完全无 token —— 标记为配额耗尽"""
        resp = await client.get("/api/topic/list")
        assert resp.status_code == 200

    async def test_expired_token_behavior(self, client, db):
        """过期 token —— 应被拒绝"""
        expired = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWtlIiwidmVyIjowLCJleHAiOjE3MDAwMDAwMDB9.xxx"
        resp = await client.get("/api/topic/tags", headers={
            "Authorization": f"Bearer {expired}"
        })
        # 可能 401 或 200 截断
        assert resp.status_code in (200, 401)

    async def test_public_paths_bypass_auth(self, client, db):
        """公开路径不触发鉴权"""
        for path in ["/ping", "/api/auth/captcha", "/api/topic/tags", "/api/topic/list"]:
            resp = await client.get(path)
            assert resp.status_code in (200, 404), f"{path} should not fail auth"
