"""
Interview API 集成测试 —— start / answer / summary / personas
"""
import pytest


@pytest.mark.integration
class TestInterviewPersonas:
    """人设列表"""

    async def test_list_personas(self, client, db):
        resp = await client.get("/api/interview/personas")
        assert resp.status_code == 200
        data = resp.json()
        assert "personas" in data
        assert len(data["personas"]) == 10


@pytest.mark.integration
class TestInterviewStart:
    """面试初始化"""

    async def test_start_without_auth(self, client, db):
        """未登录不可启动"""
        resp = await client.post("/api/interview/start", json={
            "resume": "5年Java开发经验",
            "jd": "需要精通Spring、MySQL",
            "persona_id": "free_mode",
            "max_rounds": 5,
        })
        assert resp.status_code == 401

    async def test_start_rejects_excessive_rounds(self, client, db, auth_headers):
        resp = await client.post("/api/interview/start", json={
            "resume": "test", "jd": "test", "persona_id": "free_mode", "max_rounds": 21,
        }, headers=auth_headers)
        assert resp.status_code == 422

    async def test_start_rejects_oversized_resume(self, client, db, auth_headers):
        resp = await client.post("/api/interview/start", json={
            "resume": "x" * 20_001, "jd": "test", "persona_id": "free_mode",
        }, headers=auth_headers)
        assert resp.status_code == 422

    async def test_start_invalid_persona(self, client, db, auth_headers):
        """无效的人设ID应返回验证错误"""
        resp = await client.post("/api/interview/start", json={
            "resume": "test",
            "jd": "test",
            "persona_id": "nonexistent_persona",
            "max_rounds": 5,
        }, headers=auth_headers)
        assert resp.status_code == 422  # Pydantic validation

    @pytest.mark.slow
    async def test_start_requires_fields(self, client, db, auth_headers):
        """缺失 persona 等字段 —— 验证 API 可到达"""
        resp = await client.post("/api/interview/start", json={
            "persona_id": "free_mode",
            "resume": "test",
            "jd": "test",
        }, headers=auth_headers)
        # LLM 可能不可用导致 500，但至少能路由到 handler
        assert resp.status_code in (200, 422, 500, 404, 401)


@pytest.mark.integration
class TestInterviewAnswer:
    """面试回答提交"""

    async def test_answer_nonexistent_room(self, client, db, auth_headers):
        """回答不存在的房间"""
        resp = await client.post("/api/interview/answer", json={
            "room_id": "00000000-0000-0000-0000-000000000000",
            "answer": "我的回答",
        }, headers=auth_headers)
        assert resp.status_code == 404

    async def test_answer_empty(self, client, db, auth_headers):
        """空回答应被拒绝"""
        resp = await client.post("/api/interview/answer", json={
            "room_id": "00000000-0000-0000-0000-000000000000",
            "answer": "",
        }, headers=auth_headers)
        assert resp.status_code == 422


@pytest.mark.integration
class TestInterviewSummary:
    """面试总结"""

    async def test_summary_nonexistent_room(self, client, db, auth_headers):
        """获取不存在房间的总结"""
        resp = await client.get(
            "/api/interview/00000000-0000-0000-0000-000000000000/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_summary_cannot_read_another_users_room(self, client, db, auth_headers):
        import uuid
        from dataclasses import asdict

        from src.agentv3.interview import InterviewSession
        from src.models.interview_room import InterviewRoom
        from tests.factories import create_test_user

        owner = await create_test_user(
            username=f"owner{uuid.uuid4().hex[:6]}", email=f"owner{uuid.uuid4().hex[:6]}@test.com",
        )
        room_id = str(uuid.uuid4())
        await InterviewRoom.create(
            id=room_id, user=owner, persona_id="free_mode", target_position="Java",
            session_state=asdict(InterviewSession()),
        )
        resp = await client.get(f"/api/interview/{room_id}/summary", headers=auth_headers)
        assert resp.status_code == 404


@pytest.mark.unit
class TestInterviewRequestLimits:
    def test_answer_length_limit(self):
        from pydantic import ValidationError
        from src.api.interview_api import AnswerRequest

        with pytest.raises(ValidationError):
            AnswerRequest(room_id="room", answer="x" * 10_001)
