"""R-001 NL-to-SQL AST 安全边界回归测试。"""
import pytest

from src.agentv3.capabilities.query_db import normalize_readonly_sql

pytestmark = [pytest.mark.unit, pytest.mark.security]


@pytest.mark.parametrize("sql", [
    "SELECT id, topic FROM topic",
    "SELECT COUNT(*) FROM topic",
    "WITH recent AS (SELECT id FROM topic LIMIT 10) SELECT id FROM recent",
    "SELECT t.topic FROM topic t JOIN topic_reference r ON r.topic_id = t.id",
])
def test_allows_bounded_business_queries(sql):
    normalized, error = normalize_readonly_sql(sql)
    assert error == ""
    assert normalized is not None
    assert "LIMIT" in normalized


@pytest.mark.parametrize("sql", [
    "SELECT * FROM users",
    "SELECT * FROM pg_catalog.pg_user",
    "SELECT pg_sleep(10) FROM topic",
    "SELECT current_setting('data_directory') FROM topic",
    "SELECT * FROM topic FOR UPDATE",
    "DELETE FROM topic",
    "UPDATE topic SET topic = 'x'",
    "WITH changed AS (DELETE FROM topic RETURNING id) SELECT * FROM changed",
    "SELECT 1; DELETE FROM topic",
    "SET statement_timeout = 0; SELECT * FROM topic",
    "COPY topic TO PROGRAM 'id'",
])
def test_rejects_unsafe_sql(sql):
    normalized, error = normalize_readonly_sql(sql)
    assert normalized is None
    assert error


def test_clamps_outer_limit():
    normalized, error = normalize_readonly_sql("SELECT id FROM topic LIMIT 999999")
    assert error == ""
    assert normalized is not None
    assert normalized.endswith("LIMIT 100")


def test_rejects_excessive_joins():
    sql = """SELECT t.id FROM topic t
    JOIN topic_reference a ON a.topic_id=t.id
    JOIN topic_reference b ON b.topic_id=t.id
    JOIN topic_reference c ON c.topic_id=t.id
    JOIN topic_reference d ON d.topic_id=t.id
    JOIN topic_reference e ON e.topic_id=t.id"""
    normalized, error = normalize_readonly_sql(sql)
    assert normalized is None
    assert error == "JOIN 数量超限"
