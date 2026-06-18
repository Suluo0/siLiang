"""
TTLCache 单元测试 —— get / set / LRU / TTL 过期
"""
import pytest
import time
from src.common.cache import TTLCache


@pytest.mark.unit
class TestTTLCache:
    """TTL 缓存纯逻辑测试"""

    def test_set_and_get(self):
        cache = TTLCache(max_size=10, default_ttl=300)
        cache.set("key1", {"value": 42})
        assert cache.get("key1") == {"value": 42}

    def test_get_missing_returns_none(self):
        cache = TTLCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self):
        cache = TTLCache(max_size=10, default_ttl=0)  # 立即过期
        cache.set("key", "value")
        time.sleep(0.01)  # 让 TTL=0 过期
        assert cache.get("key") is None

    def test_custom_ttl(self):
        cache = TTLCache(max_size=10, default_ttl=300)
        cache.set("short", "data", ttl=-1)  # 已过期
        assert cache.get("short") is None

        cache.set("long", "data", ttl=60)
        assert cache.get("long") == "data"

    def test_lru_eviction(self):
        cache = TTLCache(max_size=3, default_ttl=300)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        # 满了
        cache.set("d", 4)
        # a 应被淘汰（最早插入，最久未使用）
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_lru_reorder_on_get(self):
        cache = TTLCache(max_size=3, default_ttl=300)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        # 访问 a，将其移到最新
        cache.get("a")
        cache.set("d", 4)
        # b 应被淘汰（a 被访问过所以不是最旧的）
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_clear(self):
        cache = TTLCache(max_size=10, default_ttl=300)
        cache.set("x", 1)
        cache.set("y", 2)
        cache.clear()
        assert cache.get("x") is None
        assert cache.get("y") is None

    def test_overwrite_key(self):
        cache = TTLCache()
        cache.set("key", "old")
        cache.set("key", "new")
        assert cache.get("key") == "new"

    def test_json_roundtrip(self):
        """验证复杂对象经过 JSON 序列化/反序列化后正确"""
        cache = TTLCache()
        data = {"nested": {"a": [1, 2, 3]}, "none": None}
        cache.set("complex", data)
        assert cache.get("complex") == data
