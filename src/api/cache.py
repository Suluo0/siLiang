"""
API 缓存中间件 —— 内存 TTL 缓存
对高频读取、低频变更的端点（/tags, /list）缓存响应
"""
import time, json
from collections import OrderedDict


class TTLCache:
    """简单的 TTL 缓存，LRU 淘汰"""

    def __init__(self, max_size: int = 50, default_ttl: int = 300):
        self._store = OrderedDict()
        self._expiry = {}
        self.max_size = max_size
        self.default_ttl = default_ttl

    def get(self, key: str):
        if key not in self._store:
            return None
        if time.time() > self._expiry.get(key, 0):
            del self._store[key]
            del self._expiry[key]
            return None
        self._store.move_to_end(key)
        return json.loads(self._store[key])

    def set(self, key: str, value, ttl: int = None):
        if key in self._store:
            self._store.move_to_end(key)
        else:
            if len(self._store) >= self.max_size:
                self._store.popitem(last=False)
        self._store[key] = json.dumps(value)
        self._expiry[key] = time.time() + (ttl or self.default_ttl)

    def clear(self):
        self._store.clear()
        self._expiry.clear()


# 全局缓存实例
cache = TTLCache(max_size=50)
