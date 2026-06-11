"""
自定义字段类型，解决 Tortoise ORM 与 PostgreSQL jsonb 兼容性问题

问题：Tortoise 0.24.2 的 JSONField.to_db_value() 返回 JSON 字符串，
     但 asyncpg 期望 jsonb 列接受 list/dict 对象
解决：覆盖 to_db_value 方法，直接返回 Python 对象，让 asyncpg 处理序列化
"""
from __future__ import annotations
from typing import TypeVar, Any, Callable, Union
from tortoise.fields import JSONField
from tortoise.exceptions import FieldError
from tortoise.models import Model

T = TypeVar("T")


class CompatibleJSONField(JSONField):
    """
    兼容 asyncpg 的 JSONB 字段
    
    PostgreSQL jsonb 列需要 asyncpg 自动序列化为 JSON bytes，
    而不是先序列化为字符串再传递
    """
    
    def __init__(
        self,
        encoder: Callable[[Any], Any] = ...,  # 不使用 encoder
        decoder: Callable[[Any], Any] = ...,
        **kwargs: Any,
    ) -> None:
        # 使用默认的 json encoder/decoder，但 to_db_value 不使用它们
        super().__init__(**kwargs)
    
    def to_db_value(
        self,
        value: Union[T, dict, list, str, bytes, None],
        instance: Union[type[Model], Model],
    ) -> Union[Any, None]:
        """
        返回 JSON 字符串，兼容 asyncpg
        """
        import json as _json
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return _json.dumps(value, ensure_ascii=False)
        if isinstance(value, str):
            return value
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)