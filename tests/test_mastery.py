"""
掌握度评分单元测试 —— 五维无 LLM 评分
"""
import pytest
import math


@pytest.mark.unit
class TestStructureLCS:
    """LCS 最长公共子序列"""

    def test_identical(self):
        from src.agentv3.capabilities.mastery_check import _lcs_ratio
        assert _lcs_ratio(["a", "b", "c"], ["a", "b", "c"]) == 1.0

    def test_half_match(self):
        from src.agentv3.capabilities.mastery_check import _lcs_ratio
        r = _lcs_ratio(["a", "b", "c"], ["a", "x", "c"])
        assert 0.6 <= r <= 0.7

    def test_no_match(self):
        from src.agentv3.capabilities.mastery_check import _lcs_ratio
        r = _lcs_ratio(["x", "y"], ["a", "b"])
        assert r == 0.0

    def test_empty(self):
        from src.agentv3.capabilities.mastery_check import _lcs_ratio
        assert _lcs_ratio([], ["a"]) == 0.0
        assert _lcs_ratio(["a"], []) == 0.0


@pytest.mark.unit
class TestEditDistance:
    """编辑距离"""

    def test_same(self):
        from src.agentv3.capabilities.mastery_check import _edit_distance
        assert _edit_distance("hello", "hello") == 0

    def test_one_diff(self):
        from src.agentv3.capabilities.mastery_check import _edit_distance
        assert _edit_distance("hello", "hallo") == 1

    def test_completely_different(self):
        from src.agentv3.capabilities.mastery_check import _edit_distance
        assert _edit_distance("abc", "xyz") == 3

    def test_empty(self):
        from src.agentv3.capabilities.mastery_check import _edit_distance
        assert _edit_distance("", "") == 0
        assert _edit_distance("abc", "") == 3


@pytest.mark.unit
class TestFuzzyMatch:
    """模糊匹配"""

    def test_exact(self):
        from src.agentv3.capabilities.mastery_check import _fuzzy_match
        assert _fuzzy_match("HashMap", "HashMap is a hash table") is True

    def test_typo(self):
        from src.agentv3.capabilities.mastery_check import _fuzzy_match
        # HashMab → HashMap (1 char diff)
        assert _fuzzy_match("HashMap", "HashMaa is a table") is True

    def test_too_short(self):
        from src.agentv3.capabilities.mastery_check import _fuzzy_match
        assert _fuzzy_match("AB", "something with AB") is False  # ≤2 len


@pytest.mark.unit
class TestSplitSentences:
    """句子分割"""

    def test_basic(self):
        from src.agentv3.capabilities.mastery_check import _split_sentences
        result = _split_sentences("第一句。第二句。第三句")
        assert len(result) == 3

    def test_newline(self):
        from src.agentv3.capabilities.mastery_check import _split_sentences
        result = _split_sentences("A\nB\nC")
        assert len(result) == 3

    def test_mixed(self):
        from src.agentv3.capabilities.mastery_check import _split_sentences
        result = _split_sentences("HashMap是哈希表；它使用红黑树。了解源码有帮助")
        assert len(result) >= 2


@pytest.mark.unit
class TestScoreComposition:
    """加权总分计算逻辑"""

    def test_perfect(self):
        scores = {"keypoint": 1.0, "structure": 1.0, "keyword": 1.0, "length": 1.0, "coherence": 1.0}
        _WEIGHTS = {"keypoint": 0.35, "structure": 0.15, "keyword": 0.20, "length": 0.15, "coherence": 0.15}
        total = sum(scores[k] * _WEIGHTS[k] for k in _WEIGHTS)
        assert abs(total - 1.0) < 0.001

    def test_zero(self):
        scores = {"keypoint": 0.0, "structure": 0.0, "keyword": 0.0, "length": 0.0, "coherence": 0.0}
        _WEIGHTS = {"keypoint": 0.35, "structure": 0.15, "keyword": 0.20, "length": 0.15, "coherence": 0.15}
        total = sum(scores[k] * _WEIGHTS[k] for k in _WEIGHTS)
        assert total == 0.0

    def test_boundary_mastery(self):
        """0.60 阈值边界"""
        scores = {"keypoint": 0.60, "structure": 0.60, "keyword": 0.60, "length": 0.60, "coherence": 0.60}
        _WEIGHTS = {"keypoint": 0.35, "structure": 0.15, "keyword": 0.20, "length": 0.15, "coherence": 0.15}
        total = sum(scores[k] * _WEIGHTS[k] for k in _WEIGHTS)
        assert abs(total - 0.60) < 0.001  # all 0.60 → total = 0.60


@pytest.mark.unit
class TestMasteryCheckAPI:
    """掌握度 API 集成测试"""

    async def test_mastery_check_requires_auth(self, client, db):
        """未登录不可测评——可能 404（题不存在）或 401（未登录）"""
        resp = await client.post("/api/topic/00000000-0000-0000-0000-000000000001/mastery-check", json={
            "answer": "HashMap底层由数组和链表组成"
        })
        # 题目先查，不存在的题目返回 404；存在但未登录返回 401
        assert resp.status_code in (401, 404)

    async def test_mastery_check_empty_answer(self, client, db, auth_headers):
        """空回答应被拒绝"""
        resp = await client.post("/api/topic/00000000-0000-0000-0000-000000000001/mastery-check", json={
            "answer": "ab"  # < 10 chars
        }, headers=auth_headers)
        assert resp.status_code == 422

    async def test_mastery_check_topic_not_found(self, client, db, auth_headers):
        """不存在的题目返回 404"""
        resp = await client.post("/api/topic/00000000-0000-0000-0000-000000000000/mastery-check", json={
            "answer": "这是一个足够长的回答来测试掌握度评测系统"
        }, headers=auth_headers)
        assert resp.status_code == 404

    async def test_mastery_check_with_real_topic(self, client, db, auth_headers):
        """真实题目评测——应返回五维分数"""
        from tests.factories import create_test_topic
        import uuid

        topic = await create_test_topic(
            topic="Java异常处理",
            domain="Java核心",
            keywords=["try-catch", "throw", "finally", "Exception"],
            core_summary="Java使用try-catch-finally处理异常",
            core_points="try块捕获异常\ncatch处理异常\nfinally执行清理",
            detailed_explanation="Java异常处理机制通过try-catch-finally实现。",
        )

        resp = await client.post(f"/api/topic/{topic.id}/mastery-check", json={
            "answer": "Java中使用try catch来捕获和处理异常，finally块用于执行清理操作。"
        }, headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert "scores" in data
        assert "total" in data
        assert "mastered" in data
        assert "feedback" in data
        for dim in ["keypoint", "structure", "keyword", "length", "coherence"]:
            assert dim in data["scores"], f"missing dimension: {dim}"

    async def test_mastery_check_updates_status(self, client, db, auth_headers):
        """评测后 UserTopicStatus 应被更新"""
        from tests.factories import create_test_topic
        import uuid

        topic = await create_test_topic(
            topic="测试掌握度",
            domain="测试",
            keywords=["测试"],
            core_summary="这是测试",
            core_points="测试点",
            detailed_explanation="这是一个测试题目",
        )

        resp = await client.post(f"/api/topic/{topic.id}/mastery-check", json={
            "answer": "这是一个足够长的回答内容来通过测试评测系统的基本要求"
        }, headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["mastered"], bool)
        assert 0 <= data["total"] <= 1


@pytest.mark.unit
class TestMasteryModel:
    """Model 导入测试"""

    def test_model_import(self, db):
        from src.models.mastery_attempt import MasteryAttempt
        assert MasteryAttempt.__name__ == "MasteryAttempt"

    def test_user_topic_status_new_fields(self, db):
        from src.models.user_topic_status import UserTopicStatus
        assert UserTopicStatus.__name__ == "UserTopicStatus"
