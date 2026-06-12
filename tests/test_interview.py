"""
模拟面试系统单元测试
测试内容：
1. 路由决策算法
2. 评分分类
3. 关键词命中率
4. PersonaManager
5. InterviewSession 上下文聚合 + 总结
6. 数据模型可导入
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ═══════════════════════════════════════════
# 1. 路由决策测试
# ═══════════════════════════════════════════

class TestRouteDecision:
    """测试 decide_route 路由决策算法"""

    def test_score_excellent_returns_derivative(self):
        from src.agentv3.interview.router import decide_route, ROUTE_DERIVATIVE
        assert decide_route(0.95, 1, 0) == ROUTE_DERIVATIVE
        assert decide_route(0.80, 1, 0) == ROUTE_DERIVATIVE

    def test_score_good_returns_extension(self):
        from src.agentv3.interview.router import decide_route, ROUTE_EXTENSION
        assert decide_route(0.79, 1, 0) == ROUTE_EXTENSION
        assert decide_route(0.50, 1, 0) == ROUTE_EXTENSION

    def test_score_weak_returns_prerequisite(self):
        from src.agentv3.interview.router import decide_route, ROUTE_PREREQUISITE
        assert decide_route(0.49, 1, 0) == ROUTE_PREREQUISITE
        assert decide_route(0.30, 1, 0) == ROUTE_PREREQUISITE

    def test_score_very_low_returns_summary(self):
        from src.agentv3.interview.router import decide_route, ROUTE_SUMMARY
        assert decide_route(0.29, 1, 0) == ROUTE_SUMMARY
        assert decide_route(0.10, 1, 0) == ROUTE_SUMMARY

    def test_max_rounds_returns_summary(self):
        from src.agentv3.interview.router import decide_route, MAX_ROUNDS, ROUTE_SUMMARY
        assert decide_route(0.95, MAX_ROUNDS, 0) == ROUTE_SUMMARY
        assert decide_route(0.95, MAX_ROUNDS + 1, 0) == ROUTE_SUMMARY

    def test_consecutive_low_returns_summary(self):
        from src.agentv3.interview.router import decide_route, ROUTE_SUMMARY
        assert decide_route(0.60, 3, 2) == ROUTE_SUMMARY  # 2 consecutive lows
        assert decide_route(0.60, 3, 3) == ROUTE_SUMMARY

    def test_consecutive_low_resets_on_good_score(self):
        from src.agentv3.interview.router import get_next_consecutive_low
        assert get_next_consecutive_low(0.85, 2) == 0
        assert get_next_consecutive_low(0.50, 2) == 0
        assert get_next_consecutive_low(0.29, 0) == 1
        assert get_next_consecutive_low(0.10, 1) == 2


# ═══════════════════════════════════════════
# 2. 关键词命中率测试
# ═══════════════════════════════════════════

class TestKeywordHitRate:
    """测试关键词命中率计算"""

    def test_full_hit(self):
        from src.agentv3.capabilities.score_answer import _keyword_hit_rate
        assert _keyword_hit_rate(["HashMap", "红黑树"], "HashMap底层使用红黑树") == 1.0

    def test_partial_hit(self):
        from src.agentv3.capabilities.score_answer import _keyword_hit_rate
        assert _keyword_hit_rate(["HashMap", "红黑树"], "HashMap是哈希表") == 0.5

    def test_no_hit(self):
        from src.agentv3.capabilities.score_answer import _keyword_hit_rate
        assert _keyword_hit_rate(["HashMap", "红黑树"], "我不知道") == 0.0

    def test_empty_points(self):
        from src.agentv3.capabilities.score_answer import _keyword_hit_rate
        assert _keyword_hit_rate([], "anything") == 1.0


# ═══════════════════════════════════════════
# 3. 评分分类测试
# ═══════════════════════════════════════════

class TestScoreLabel:
    """测试评分标签分类"""

    def test_classify_label(self):
        from src.agentv3.capabilities.score_answer import _classify_label
        assert _classify_label(0.95) == "优秀"
        assert _classify_label(0.80) == "优秀"
        assert _classify_label(0.65) == "良好"
        assert _classify_label(0.40) == "一般"
        assert _classify_label(0.39) == "较差"
        assert _classify_label(0.0) == "较差"


# ═══════════════════════════════════════════
# 4. PersonaManager 测试
# ═══════════════════════════════════════════

class TestPersonaManager:
    """测试面试官人设管理"""

    def test_list_ids(self):
        from src.agentv3.interview.persona import PersonaManager
        ids = PersonaManager.list_ids()
        assert len(ids) == 10
        assert "ali_p7" in ids
        assert "free_mode" in ids

    def test_load_valid_prompt(self):
        from src.agentv3.interview.persona import PersonaManager
        prompt = PersonaManager.load_prompt("free_mode")
        assert len(prompt) > 0
        assert "面试官" in prompt

    def test_load_invalid_prompt_raises(self):
        from src.agentv3.interview.persona import PersonaManager
        with pytest.raises(ValueError, match="未知的人设ID"):
            PersonaManager.load_prompt("nonexistent")

    def test_compile_prompt(self):
        from src.agentv3.interview.persona import PersonaManager
        prompt = PersonaManager.compile_prompt("free_mode", {
            "candidate_name": "张三",
            "target_position": "后端开发",
        })
        assert "后端开发" in prompt

    def test_cache(self):
        from src.agentv3.interview.persona import PersonaManager
        prompt1 = PersonaManager.load_prompt("free_mode")
        prompt2 = PersonaManager.load_prompt("free_mode")
        assert prompt1 is prompt2


# ═══════════════════════════════════════════
# 5. InterviewSession 聚合 + 总结
# ═══════════════════════════════════════════

class TestInterviewSession:
    """测试面试会话核心逻辑"""

    def test_aggregate_context(self):
        from src.agentv3.interview.session import InterviewSession
        session = InterviewSession(persona_id="free_mode")
        session._aggregate_context({
            "knowledge_gaps": ["HashMap原理"],
            "demonstrated_skills": ["Java基础"],
        })
        assert "HashMap原理" in session.aggregated_context["overall_weaknesses"]
        assert "Java基础" in session.aggregated_context["overall_strengths"]

    def test_aggregate_dedup(self):
        from src.agentv3.interview.session import InterviewSession
        session = InterviewSession(persona_id="free_mode")
        session._aggregate_context({"knowledge_gaps": ["A"], "demonstrated_skills": ["B"]})
        session._aggregate_context({"knowledge_gaps": ["A"], "demonstrated_skills": ["B"]})
        assert session.aggregated_context["overall_weaknesses"].count("A") == 1
        assert session.aggregated_context["overall_strengths"].count("B") == 1

    def test_summary_empty(self):
        from src.agentv3.interview.session import InterviewSession
        session = InterviewSession(persona_id="free_mode")
        s = session.summary()
        assert s["total_rounds"] == 0
        assert s["overall_score"] == 0.0

    def test_summary_with_rounds(self):
        from src.agentv3.interview.session import InterviewSession
        session = InterviewSession(persona_id="free_mode")
        session.rounds = [
            {"scores": {"total": 0.9, "accuracy": 0.9, "depth": 0.8, "completeness": 0.9, "clarity": 0.9, "practical": 0.9}},
            {"scores": {"total": 0.7, "accuracy": 0.7, "depth": 0.6, "completeness": 0.7, "clarity": 0.7, "practical": 0.7}},
        ]
        s = session.summary()
        assert s["total_rounds"] == 2
        assert round(s["overall_score"], 2) == 0.80
        assert round(s["accuracy_avg"], 2) == 0.80

    def test_submit_answer_without_setup_raises(self):
        import pytest
        from src.agentv3.interview.session import InterviewSession
        session = InterviewSession(persona_id="free_mode")
        with pytest.raises(RuntimeError, match="面试尚未初始化"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                session.submit_answer("test")
            )


# ═══════════════════════════════════════════
# 6. 数据模型导入测试
# ═══════════════════════════════════════════

class TestModels:
    """验证新模型可导入且结构正确"""

    def test_interview_persona_import(self):
        from src.models import InterviewPersona
        assert InterviewPersona.__name__ == "InterviewPersona"
        assert InterviewPersona._meta.db_table == "interview_persona"

    def test_interview_room_import(self):
        from src.models import InterviewRoom
        assert InterviewRoom.__name__ == "InterviewRoom"
        assert InterviewRoom._meta.db_table == "interview_room"

    def test_interview_round_import(self):
        from src.models import InterviewRound
        assert InterviewRound.__name__ == "InterviewRound"
        assert InterviewRound._meta.db_table == "interview_round"

    def test_interview_summary_import(self):
        from src.models import InterviewSummary
        assert InterviewSummary.__name__ == "InterviewSummary"
        assert InterviewSummary._meta.db_table == "interview_summary"

    def test_user_topic_status_new_fields(self):
        from src.models import UserTopicStatus
        assert UserTopicStatus.__name__ == "UserTopicStatus"
        assert UserTopicStatus._meta.db_table == "user_topic_status"


# ═══════════════════════════════════════════
# 7. 能力导入测试
# ═══════════════════════════════════════════

class TestCapabilities:
    """验证新能力可导入且函数签名正确"""

    def test_score_answer_import(self):
        from src.agentv3.capabilities.score_answer import score_answer
        import inspect
        assert inspect.iscoroutinefunction(score_answer)

    def test_extract_context_import(self):
        from src.agentv3.capabilities.extract_context import extract_context
        import inspect
        assert inspect.iscoroutinefunction(extract_context)

    def test_generate_followup_import(self):
        from src.agentv3.capabilities.generate_followup import generate_followup
        import inspect
        assert inspect.iscoroutinefunction(generate_followup)

    def test_analyze_resume_import(self):
        from src.agentv3.capabilities.analyze_resume import analyze_resume
        import inspect
        assert inspect.iscoroutinefunction(analyze_resume)

    def test_analyze_jd_import(self):
        from src.agentv3.capabilities.analyze_jd import analyze_jd
        import inspect
        assert inspect.iscoroutinefunction(analyze_jd)

    def test_match_resume_jd_import(self):
        from src.agentv3.capabilities.match_resume_jd import match_resume_jd
        import inspect
        assert inspect.iscoroutinefunction(match_resume_jd)

    def test_publish_event_import(self):
        from src.agentv3.capabilities.publish_event import publish_interview_event
        import inspect
        assert inspect.iscoroutinefunction(publish_interview_event)
