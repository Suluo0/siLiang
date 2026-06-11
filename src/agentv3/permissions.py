"""
权限枚举 —— 编译期受保护的权限标签
"""
from enum import StrEnum


class Permission(StrEnum):
    # 读权限
    READ = "read"
    LLM_INVOKE = "llm:invoke"
    DB_QUERY = "db:query"

    # 写权限
    WRITE = "write"
    DB_WRITE = "db:write"
    DB_DELETE = "db:delete"
    DB_MILVUS = "db:milvus"

    # 管理权限
    ADMIN = "admin"
