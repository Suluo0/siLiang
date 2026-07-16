"""NL-to-SQL 只读查询能力。

安全边界同时由 SQLGlot AST allowlist 和 PostgreSQL 只读账号/事务提供，
不把 LLM 输出、正则或应用主连接当作安全边界。
"""
import json
import logging

import asyncpg
from sqlglot import exp, parse
from sqlglot.errors import ParseError

from src.config.settings import settings
from src.tools.llm_client import LLMClient
from src.tools.schema_manager import build_schema_prompt
from src.utils import clean_json

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 50
MAX_LIMIT = 100
STATEMENT_TIMEOUT_MS = 3_000
LOCK_TIMEOUT_MS = 1_000

ALLOWED_TABLES = {
    "topic", "topic_prerequisite", "topic_core_concept", "topic_derivative",
    "topic_extension", "topic_evaluation_anchor", "topic_similar_question",
    "topic_advanced_question", "topic_reference", "topic_review_log",
    "knowledge_dict", "knowledge_alias", "user_topic_status",
    "user_topic_progress", "job_position", "interview_persona",
    "interview_room", "interview_round", "interview_summary",
}
ALLOWED_FUNCTIONS = {
    "avg", "coalesce", "count", "date_trunc", "greatest", "least", "lower",
    "max", "min", "nullif", "round", "sum", "upper",
}
BLOCKED_NODE_TYPES = tuple(
    node_type for node_type in (
        getattr(exp, name, None) for name in (
            "Alter", "Command", "Copy", "Create", "Delete", "Drop", "Execute",
            "Grant", "Insert", "Lock", "Merge", "Pragma", "Set", "Transaction",
            "TruncateTable", "Update", "Use",
        )
    ) if node_type is not None
)

_BASE_SKILL = """你是 PostgreSQL SQL 生成器。根据用户意图和提供的 schema 生成一条只读查询。
只能使用 schema 中的业务表，禁止系统表、写操作、锁、会话命令和任意函数。
必须输出 JSON：{"sql":"SELECT ... LIMIT 50","explanation":"简短说明"}。
"""


def _function_name(node: exp.Func) -> str:
    if isinstance(node, exp.Anonymous):
        return node.name.lower()
    return node.sql_name().lower()


def normalize_readonly_sql(sql: str) -> tuple[str | None, str]:
    """解析并规范化单条只读 SQL；失败时返回稳定、不泄露内部细节的原因。"""
    if not sql or not sql.strip():
        return None, "SQL 为空"
    try:
        statements = parse(sql, read="postgres")
    except ParseError:
        return None, "SQL 语法不合法"
    if len(statements) != 1:
        return None, "只允许一条 SQL"

    statement = statements[0]
    if not isinstance(statement, exp.Query):
        return None, "只允许 SELECT 查询"
    if any(isinstance(node, BLOCKED_NODE_TYPES) for node in statement.walk()):
        return None, "SQL 包含禁止操作"

    cte_names = {cte.alias_or_name.lower() for cte in statement.find_all(exp.CTE)}
    tables = list(statement.find_all(exp.Table))
    for table in tables:
        if table.catalog or table.db or (
            table.name.lower() not in ALLOWED_TABLES and table.name.lower() not in cte_names
        ):
            return None, f"禁止查询非业务表: {table.name}"
    if len(list(statement.find_all(exp.Join))) > 4:
        return None, "JOIN 数量超限"
    for subquery in statement.find_all(exp.Subquery):
        depth = 1
        parent = subquery.parent
        while parent is not None:
            depth += isinstance(parent, exp.Subquery)
            parent = parent.parent
        if depth > 2:
            return None, "子查询层级超限"
    for function in statement.find_all(exp.Func):
        name = _function_name(function)
        if name not in ALLOWED_FUNCTIONS:
            return None, f"禁止调用函数: {name}"

    limit = statement.args.get("limit")
    limit_value = None
    if limit and isinstance(limit.expression, exp.Literal) and limit.expression.is_int:
        limit_value = int(limit.expression.this)
    statement = statement.limit(min(limit_value or DEFAULT_LIMIT, MAX_LIMIT), copy=False)
    return statement.sql(dialect="postgres"), ""


def validate_sql(sql: str) -> tuple[bool, str]:
    normalized, error = normalize_readonly_sql(sql)
    return normalized is not None, error


def enforce_limit(sql: str) -> str:
    normalized, error = normalize_readonly_sql(sql)
    if normalized is None:
        raise ValueError(error)
    return normalized


async def _execute_readonly(sql: str) -> list[dict]:
    if not settings.DATABASE_READ_URL:
        raise RuntimeError("DATABASE_READ_URL is required")
    connection = await asyncpg.connect(settings.DATABASE_READ_URL, timeout=3)
    try:
        async with connection.transaction(readonly=True):
            await connection.execute(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT_MS}ms'")
            await connection.execute(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT_MS}ms'")
            rows = await connection.fetch(sql)
            return [dict(row) for row in rows]
    finally:
        await connection.close()


async def query_database(query: str, context: str = "") -> dict:
    schema_text = build_schema_prompt(query)
    prompt = f"查询意图：{query}"
    if context:
        prompt += f"\n附加上下文：{context}"

    raw = await LLMClient.get_instance().ainvoke(
        query=prompt, system_prompt=_BASE_SKILL + "\n" + schema_text,
        temperature=0.1, max_tokens=2048, json_mode=True,
    )
    try:
        parsed = json.loads(clean_json(raw))
    except (json.JSONDecodeError, TypeError):
        return {"sql": "", "results": [], "row_count": 0, "explanation": "", "error": "SQL 生成结果无效"}

    raw_sql = parsed.get("sql", "")
    explanation = parsed.get("explanation", "")
    sql, error = normalize_readonly_sql(raw_sql)
    if sql is None:
        return {"sql": raw_sql, "results": [], "row_count": 0, "explanation": explanation, "error": error}
    try:
        rows = await _execute_readonly(sql)
    except Exception:
        logger.exception("NL-to-SQL readonly query failed")
        return {"sql": sql, "results": [], "row_count": 0, "explanation": explanation, "error": "查询执行失败"}
    return {"sql": sql, "results": rows, "row_count": len(rows), "explanation": explanation}
