"""
未覆盖 Model CRUD 集成测试 —— Menu / Captcha / Outbox / UserQuota /
JobPosition / PromptTemplate / PromptCallLog
"""
import pytest
import uuid


@pytest.mark.integration
class TestMenuCRUD:
    """菜单表"""

    async def test_create_and_list(self, client, db):
        from src.models import Menu
        import uuid as _u

        mid1 = abs(hash(str(_u.uuid4()))) % 100000 + 10000
        mid2 = mid1 + 1
        await Menu.create(id=mid1, name=f"m_{mid1}", path=f"/m{mid1}", icon="HomeFilled",
                          parent_id=None, sort_order=mid1, is_visible=True,
                          component=f"/m{mid1}/idx")
        await Menu.create(id=mid2, name=f"m_{mid2}", path=f"/m{mid2}", icon=None,
                          parent_id=mid1, sort_order=mid2, is_visible=True,
                          component=f"/m{mid2}/idx")

        found = await Menu.filter(id=mid1).first()
        assert found is not None

    async def test_filter_visible(self, client, db):
        from src.models import Menu
        import uuid as _u

        vid = abs(hash(str(_u.uuid4()))) % 100000 + 20000
        hid = vid + 1
        await Menu.create(id=vid, name=f"vmenu_{vid}", path=f"/vmenu{vid}", icon=None,
                          parent_id=None, sort_order=vid, is_visible=True, component=f"/vm{vid}")
        await Menu.create(id=hid, name=f"hmenu_{hid}", path=f"/hmenu{hid}", icon=None,
                          parent_id=None, sort_order=hid, is_visible=False, component=f"/hm{hid}")

        visible = await Menu.filter(is_visible=True).count()
        assert visible >= 1


@pytest.mark.integration
class TestCaptchaCRUD:
    """验证码表"""

    async def test_create_and_expire(self, client, db):
        from src.models.captcha import Captcha

        cid = str(uuid.uuid4())
        captcha = await Captcha.create(id=cid, code="ABCD")

        found = await Captcha.filter(id=cid).first()
        assert found is not None
        assert found.code == "ABCD"

    async def test_used_flag(self, client, db):
        from src.models.captcha import Captcha

        cid = str(uuid.uuid4())
        await Captcha.create(id=cid, code="1234", used=False)
        c = await Captcha.filter(id=cid, used=False).first()
        assert c is not None


@pytest.mark.integration
class TestOutboxCRUD:
    """Outbox 补偿表"""

    async def test_create_pending_event(self, client, db):
        from src.models.outbox import Outbox

        oid = str(uuid.uuid4())
        evt = await Outbox.create(
            id=oid, event_type="TOPIC_CREATED",
            payload={"topic_id": str(uuid.uuid4()), "core_concept": "Test"},
            status="PENDING", retry_count=0,
        )
        found = await Outbox.filter(id=oid).first()
        assert found is not None
        assert found.event_type == "TOPIC_CREATED"
        assert found.status == "PENDING"

    async def test_retry_tracking(self, client, db):
        from src.models.outbox import Outbox

        oid = str(uuid.uuid4())
        await Outbox.create(id=oid, event_type="TEST", payload={},
                            status="FAILED", retry_count=3, error_message="timeout")
        o = await Outbox.filter(id=oid).first()
        assert o.retry_count == 3


@pytest.mark.integration
class TestUserQuotaCRUD:
    """用户配额表"""

    async def test_create_with_user(self, client, db):
        from src.models.user import User
        from src.models.user_quota import UserQuota
        from src.auth.hash import hash_password

        uid = str(uuid.uuid4())
        await User.create(id=uid, username=f"quota{uuid.uuid4().hex[:6]}",
                          email=f"quota{uuid.uuid4().hex[:6]}@test.com",
                          password_hash=hash_password("Test123"), is_active=True, token_version=0)

        q = await UserQuota.create(id=str(uuid.uuid4()), user_id=uid,
                                   agent_credits=5, topic_credits=20)
        assert q.agent_credits == 5
        assert q.topic_credits == 20

    async def test_update_credits(self, client, db):
        from src.models.user_quota import UserQuota

        found = await UserQuota.all().first()
        if found:
            found.topic_credits -= 1
            await found.save()
            refreshed = await UserQuota.filter(id=found.id).first()
            assert refreshed.topic_credits == found.topic_credits


@pytest.mark.integration
class TestJobPositionCRUD:
    """岗位表（id 为 IntField 自增）"""

    async def test_create(self, client, db):
        from src.models.job_position import JobPosition

        p = await JobPosition.create(name="测试岗", category="测试", sort_order=999)
        assert p.id is not None
        assert p.name == "测试岗"
        assert isinstance(p.id, int)


@pytest.mark.integration
class TestPromptTemplateCRUD:
    """提示词模板表"""

    async def test_create_template(self, client, db):
        from src.models.prompt_template import PromptTemplate

        pid = str(uuid.uuid4())
        tname = f"tpl_{uuid.uuid4().hex[:8]}"
        t = await PromptTemplate.create(
            id=pid, name=tname, user_prompt_template="这是 {topic} 的提示词",
            version=1, is_active=True,
        )
        found = await PromptTemplate.filter(id=pid).first()
        assert found is not None
        assert found.user_prompt_template is not None


@pytest.mark.integration
class TestPromptCallLogCRUD:
    """LLM 调用日志表"""

    async def test_log_call_with_template(self, client, db):
        from src.models.prompt_call_log import PromptCallLog
        from src.models.prompt_template import PromptTemplate

        pid = str(uuid.uuid4())
        tname = f"logt_{uuid.uuid4().hex[:8]}"
        await PromptTemplate.create(id=pid, name=tname, user_prompt_template="test",
                                    version=1, is_active=True)

        log_id = str(uuid.uuid4())
        log = await PromptCallLog.create(
            id=log_id, prompt_template_id=pid,
            trace_id=str(uuid.uuid4())[:64],
            capability_id="test_cap",
            status="success", duration_ms=150, model="deepseek-chat",
            user_prompt="hello",
            output_content="response",
        )
        found = await PromptCallLog.filter(id=log_id).first()
        assert found is not None

    async def test_log_error(self, client, db):
        from src.models.prompt_call_log import PromptCallLog
        from src.models.prompt_template import PromptTemplate

        pid = str(uuid.uuid4())
        tname = f"err_{uuid.uuid4().hex[:8]}"
        await PromptTemplate.create(id=pid, name=tname, user_prompt_template="x",
                                    version=1, is_active=True)

        log = await PromptCallLog.create(
            id=str(uuid.uuid4()), prompt_template_id=pid,
            status="failed", error_message="timeout", duration_ms=30000,
        )
        assert log.error_message == "timeout"
