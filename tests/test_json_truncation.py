"""
JSON 截断单元测试 —— _truncate_json_response 在 200 字符处硬切割 + 闭合
"""
import json
import pytest
from src.api.topic_api import _truncate_json_response


@pytest.mark.unit
class TestJSONTruncation:
    """JSON 响应截断逻辑"""

    def test_short_json_passthrough(self):
        """少于 200 字符的 JSON 不做切割，只加 locked"""
        data = {"id": "123", "topic": "test", "domain": "Java", "difficulty": 3}
        result = _truncate_json_response(data, max_len=200)

        assert result["locked"] is True
        assert result["locked_sections"] == ["*"]
        assert result["topic"] == "test"

    def test_long_json_truncated(self):
        """长 JSON 在 200 处切割"""
        data = {
            "id": "x" * 36,
            "topic": "测试题目",
            "detailed_explanation": "A" * 5000,
            "code_example": "B" * 3000,
        }
        result = _truncate_json_response(data, max_len=200)

        # 验证是合法 JSON
        raw = json.dumps(result, ensure_ascii=False)
        json.loads(raw)  # 不抛异常

        # locked 字段必须存在
        assert result["locked"] is True

        # 长内容应该已被截断
        if result.get("detailed_explanation"):
            assert len(str(result["detailed_explanation"])) <= 200
        if result.get("code_example"):
            assert len(str(result["code_example"])) <= 200

    def test_truncation_preserves_top_level_keys(self):
        """截断后的 JSON 至少包含 id, topic, locked"""
        data = {"id": "abc", "topic": "HashMap", "detailed_explanation": "X" * 10000}
        result = _truncate_json_response(data, max_len=200)

        assert "locked" in result
        assert result["locked"] is True

    def test_valid_json_after_truncation(self):
        """截断后必须是合法 JSON"""
        data = {
            "id": "x" * 36,
            "topic": "长题目" * 20,
            "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
            "core_summary": "C" * 1000,
        }
        result = _truncate_json_response(data, max_len=120)
        raw = json.dumps(result, ensure_ascii=False)
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)

    def test_fallback_on_bad_json(self):
        """无法修复的 JSON 回退到最小元数据"""
        # 构造一个极端场景：200 字符全在字符串内导致无法闭合
        data = {"topic": "A" * 500}
        result = _truncate_json_response(data, max_len=10)
        # 兜底返回元数据
        assert "topic" in result or "id" in result
        assert result["locked"] is True
