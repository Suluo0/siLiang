"""
query_database capability —— NL → (Milvus表检索) → SQL → 校验 → 执行
表规模扩大后不膨胀 prompt：通过 Milvus table_schemas 动态检索相关表
"""
import re
import json
from typing import Any
from src.tools.llm_client import LLMClient
from src.tools.schema_manager import build_schema_prompt
from src.utils import clean_json

# ── 安全规则 ──

FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE",
    "TRUNCATE", "EXECUTE", "COPY", "GRANT", "REVOKE",
    "REPLACE", "MERGE", "CALL", "DO", "SET", "BEGIN", "COMMIT",
    "ROLLBACK", "SAVEPOINT", "DECLARE", "FETCH", "MOVE",
    "IMPORT", "EXPORT", "LOAD", "UNLOAD",
]

DEFAULT_LIMIT = 50
MAX_LIMIT = 100

_LIMIT_PATTERN = re.compile(r"\bLIMIT\s+(\d+)", re.IGNORECASE)
_SELECT_PATTERN = re.compile(r"^\s*SELECT\b", re.IGNORECASE)
_STRIP_COMMENTS = re.compile(r"--[^\n]*|/\*[\s\S]*?\*/")

_BASE_SKILL = """你是一个 PostgreSQL SQL 生成器。根据自然语言查询意图，利用可用的数据库表生成只读 SQL。

## 关键关联规则
- topic 通过 4 张表关联知识点：topic_prerequisite(前置)、topic_core_concept(核心)、topic_derivative(衍生)、topic_extension(扩展)
- 这 4 张表都通过 knowledge_id 关联 knowledge_dict
- user_topic_status 通过 user_id + topic_id 关联用户和题目
- topic 1:N topic_evaluation_anchor / topic_similar_question / topic_advanced_question / topic_reference

## 查询"涉及某知识点"的题目必须 UNION 四张表：
SELECT t.topic FROM topic t
JOIN topic_prerequisite tp ON t.id = tp.topic_id JOIN knowledge_dict kd ON tp.knowledge_id = kd.id WHERE kd.name = 'X'
UNION
SELECT t.topic FROM topic t
JOIN topic_core_concept tcc ON t.id = tcc.topic_id JOIN knowledge_dict kd ON tcc.knowledge_id = kd.id WHERE kd.name = 'X'
UNION ...

## 规则
1. 只输出 SELECT，禁止 INSERT/UPDATE/DELETE/DROP/ALTER
2. 必须包含 LIMIT，默认 50
3. 表别名：主表 t，知识表 kd，关联表 tp/tcc/td/te
4. 字符串用单引号
5. NULL 比较用 IS NULL / IS NOT NULL
6. 子查询不超过 2 层
7. 参数占位符用 ?
8. 禁止 PostgreSQL 特有语法，除 schema 中定义的列名外

## 输出格式
{"sql": "SELECT ...", "explanation": "简短说明(15字)"}

只输出 JSON，不要其他文字。"""


def validate_sql(sql: str) -> tuple[bool, str]:
    cleaned = _STRIP_COMMENTS.sub("", sql).strip()
    if not cleaned:
        return False, "SQL 为空"
    if not _SELECT_PATTERN.match(cleaned):
        return False, "只允许 SELECT 语句"
    upper = cleaned.upper()
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(r"\b" + kw + r"\b", upper):
            return False, f"禁止使用 {kw}"
    semicolons = [m.start() for m in re.finditer(r";", cleaned)]
    for pos in semicolons:
        after = cleaned[pos + 1:].strip()
        if after and not after.startswith("--"):
            return False, "不支持多条 SQL 语句"
    return True, ""


def enforce_limit(sql: str) -> str:
    cleaned = _STRIP_COMMENTS.sub("", sql).rstrip(";").strip()
    if not _LIMIT_PATTERN.search(cleaned):
        return cleaned + f" LIMIT {DEFAULT_LIMIT}"
    match = _LIMIT_PATTERN.search(cleaned)
    if match and int(match.group(1)) > MAX_LIMIT:
        return _LIMIT_PATTERN.sub(f"LIMIT {MAX_LIMIT}", cleaned)
    return cleaned


async def query_database(query: str, context: str = "") -> dict:
    """
    自然语言 → (Milvus 检索相关表) → SQL → 执行
    """
    llm = LLMClient.get_instance()

    # 动态构建表结构 prompt
    schema_text = build_schema_prompt(query)
    system_prompt = _BASE_SKILL + "\n\n" + schema_text

    prompt = f"查询意图：{query}"
    if context:
        prompt += f"\n附加上下文：{context}"
    prompt += "\n\n生成 SQL 查询。直接输出 JSON，不要有任何其他文字。"

    raw = await llm.ainvoke(
        query=prompt, system_prompt=system_prompt,
        temperature=0.1, max_tokens=2048,
        json_mode=True,
    )

    parsed = json.loads(clean_json(raw))
    sql = parsed.get("sql", "")
    explanation = parsed.get("explanation", "")

    is_safe, error = validate_sql(sql)
    if not is_safe:
        return {
            "sql": sql, "results": [], "row_count": 0,
            "explanation": explanation, "error": error,
        }

    sql = enforce_limit(sql)

    import asyncpg
    from tortoise import connections

    try:
        conn = connections.get("default")
    except Exception:
        return {
            "sql": sql, "results": [], "row_count": 0,
            "explanation": explanation, "error": "DB 连接不可用",
        }

    try:
        rows = await conn.execute_query_dict(sql)
        return {
            "sql": sql, "results": [dict(r) for r in rows],
            "row_count": len(rows), "explanation": explanation,
        }
    except Exception as e:
        return {
            "sql": sql, "results": [], "row_count": 0,
            "explanation": explanation, "error": str(e),
        }
