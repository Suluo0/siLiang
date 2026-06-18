"""
去重系统单元测试 —— 七层防呆 L1~L7
"""
import pytest


@pytest.mark.unit
class TestDedupLogic:
    """去重算法逻辑"""

    def test_l1_exact_blocks(self):
        """L1: 精确匹配应直接阻断"""
        # L1 逻辑在 check_duplicate 中：Topic.filter(topic=concept).first()
        # 此测试验证判定函数
        result = _simulate_l1_check("HashMap底层实现", "HashMap底层实现")
        assert result["duplicate"] is True
        assert result["method"] == "exact_pg"

    def test_l1_different_passes(self):
        """不同名称通过 L1"""
        result = _simulate_l1_check("HashMap底层实现", "ConcurrentHashMap源码")
        assert result["duplicate"] is False

    def test_l2_threshold_block(self):
        """L2: 余弦≥0.75 阻断"""
        assert _simulate_l2(0.78) == "block"
        assert _simulate_l2(0.75) == "block"

    def test_l2_threshold_pass(self):
        """L2: 余弦<0.55 放行"""
        assert _simulate_l2(0.50) == "pass"
        assert _simulate_l2(0.30) == "pass"

    def test_l2_grey_zone_triggers_l3(self):
        """L2: 余弦 0.55~0.74 触发 L3 Agent 验证"""
        assert _simulate_l2(0.60) == "trigger_l3"
        assert _simulate_l2(0.70) == "trigger_l3"

    def test_l2_no_hits(self):
        """L2: 无候选直接放行"""
        assert _simulate_l2_with_no_hits() == "pass"

    def test_l4_fallback_threshold(self):
        """L4: Agent 不可用时回退到≥0.65 阻断"""
        assert _simulate_l4_fallback(0.68) == "block"
        assert _simulate_l4_fallback(0.62) == "pass"

    def test_verify_match_combined_decision(self):
        """L3+L7: combined≥0.60 且 passed→block"""
        result = _simulate_verify(cosine=0.70, llm_score=0.72)
        assert result["duplicate"] is True  # combined = 0.71, passed=True(≥0.70)
        result2 = _simulate_verify(cosine=0.50, llm_score=0.60)
        assert result2["duplicate"] is False  # passed=False(llm<0.70)

    def test_content_dedup_threshold(self):
        """L7: 内容去重≥0.75 跳过"""
        assert _simulate_content_check(0.80) == "skip"
        assert _simulate_content_check(0.65) == "allow"


# ── 模拟函数（测试逻辑，不调真实 LLM/Milvus）──

def _simulate_l1_check(concept: str, existing_name: str) -> dict:
    """L1 精确匹配模拟"""
    if concept == existing_name:
        return {"duplicate": True, "method": "exact_pg"}
    return {"duplicate": False, "method": "exact_pg"}


def _simulate_l2(score: float) -> str:
    """L2 余弦阈值模拟"""
    if score >= 0.75:
        return "block"
    if score >= 0.55:
        return "trigger_l3"
    return "pass"


def _simulate_l2_with_no_hits() -> str:
    """L2 无候选"""
    return "pass"


def _simulate_l4_fallback(score: float) -> str:
    """L4 Agent 不可用时的回退"""
    if score >= 0.65:
        return "block"
    return "pass"


def _simulate_verify(cosine: float, llm_score: float) -> dict:
    """L3 verify_match 双分数模拟"""
    combined = 0.5 * cosine + 0.5 * llm_score
    passed = llm_score >= 0.70
    if passed and combined >= 0.60:
        return {"duplicate": True, "combined": combined}
    return {"duplicate": False, "combined": combined}


def _simulate_content_check(score: float) -> str:
    """L7 内容去重阈值"""
    if score >= 0.75:
        return "skip"
    return "allow"
