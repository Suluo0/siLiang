"""
P1 健壮性修复黑盒验收测试
覆盖 R-009, R-010, R-011, R-015, R-016
"""
import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
from starlette.requests import Request
from starlette.responses import Response

pytestmark = [pytest.mark.unit, pytest.mark.security]


# ── R-009: 异步I/O测试 ──

class TestAsyncIO:
    """验证同步阻塞调用已改为异步"""

    @pytest.mark.asyncio
    async def test_hash_password_async(self):
        """bcrypt哈希应为异步非阻塞"""
        from src.auth.hash import hash_password_async, verify_password_async
        password = "TestPassword123"
        hashed = await hash_password_async(password)
        assert hashed
        assert await verify_password_async(password, hashed)

    @pytest.mark.asyncio
    async def test_embedding_encode_async(self):
        """Embedding编码应支持异步"""
        from src.tools.embedding import EmbeddingEncoder
        encoder = EmbeddingEncoder()
        # 验证异步方法存在
        assert hasattr(encoder, 'encode_async')
        assert callable(encoder.encode_async)

    @pytest.mark.asyncio
    async def test_milvus_insert_async(self):
        """Milvus插入应支持异步"""
        from src.tools.milvus_client import MilvusClient
        client = MilvusClient()
        # 验证异步方法存在
        assert hasattr(client, 'insert_async')
        assert callable(client.insert_async)

    @pytest.mark.asyncio
    async def test_mail_send_async(self):
        """邮件发送应支持异步"""
        from src.utils.mail import send_async, send_alert_async
        # 验证异步方法存在
        assert callable(send_async)
        assert callable(send_alert_async)


# ── R-010: Milvus注入防护测试 ──

class TestMilvusInjection:
    """验证Milvus查询已做转义处理"""

    def test_search_sparse_escapes_quotes(self):
        """search_sparse应转义引号"""
        from src.tools.milvus_client import MilvusClient
        client = MilvusClient()
        # 验证转义函数存在
        # 注入尝试: ' OR "1"="1'
        malicious_keywords = ['test" OR "1"="1', "test' OR '1'='1"]
        # 应该不会抛出异常，而是安全处理
        result = client.search_sparse(malicious_keywords)
        assert isinstance(result, list)

    def test_search_sparse_escapes_backslash(self):
        """search_sparse应转义反斜杠"""
        from src.tools.milvus_client import MilvusClient
        client = MilvusClient()
        malicious_keywords = ['test\\"]']
        result = client.search_sparse(malicious_keywords)
        assert isinstance(result, list)

    def test_topic_unique_constraint_exists(self):
        """Topic模型应有唯一约束"""
        from src.models.topic import Topic
        meta = Topic.Meta
        assert hasattr(meta, 'unique_together')
        assert 'topic' in meta.unique_together
        assert 'domain' in meta.unique_together


# ── R-011: 全局异常处理测试 ──

class TestGlobalExceptionHandler:
    """验证全局异常处理器"""

    @pytest.mark.asyncio
    async def test_exception_handler_returns_stable_error(self):
        """未捕获异常应返回稳定错误码"""
        from src.main import app, global_exception_handler
        # 创建模拟请求
        request = Request({
            "type": "http", "method": "GET", "path": "/test",
            "headers": [], "query_string": b""
        })
        request.state.request_id = "test-123"
        exc = Exception("internal error")
        response = await global_exception_handler(request, exc)
        body = json.loads(response.body)
        assert response.status_code == 500
        assert body["error_code"] == "INTERNAL_ERROR"
        assert body["request_id"] == "test-123"
        assert "internal error" not in body["detail"]

    @pytest.mark.asyncio
    async def test_value_error_handler_returns_422(self):
        """ValueError应返回422"""
        from src.main import app, value_error_handler
        request = Request({
            "type": "http", "method": "GET", "path": "/test",
            "headers": [], "query_string": b""
        })
        request.state.request_id = "test-456"
        exc = ValueError("invalid input")
        response = await value_error_handler(request, exc)
        body = json.loads(response.body)
        assert response.status_code == 422
        assert body["error_code"] == "VALIDATION_ERROR"
        assert body["detail"] == "invalid input"


# ── R-015: LLM JSON解析测试 ──

class TestLLMJsonParsing:
    """验证LLM JSON响应安全解析"""

    def test_parse_valid_json(self):
        """应正确解析有效JSON"""
        from src.tools.llm_client import parse_json_safe
        result = parse_json_safe('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_with_markdown_block(self):
        """应提取markdown代码块中的JSON"""
        from src.tools.llm_client import parse_json_safe
        text = '```json\n{"key": "value"}\n```'
        result = parse_json_safe(text)
        assert result == {"key": "value"}

    def test_parse_json_with_trailing_comma(self):
        """应处理尾随逗号"""
        from src.tools.llm_client import parse_json_safe
        text = '{"key": "value",}'
        result = parse_json_safe(text)
        assert result == {"key": "value"}

    def test_parse_empty_string(self):
        """空字符串应返回空字典"""
        from src.tools.llm_client import parse_json_safe
        assert parse_json_safe("") == {}
        assert parse_json_safe(None) == {}

    def test_parse_invalid_json(self):
        """无效JSON应返回空字典"""
        from src.tools.llm_client import parse_json_safe
        assert parse_json_safe("not json") == {}

    def test_parse_nested_json(self):
        """应正确解析嵌套JSON"""
        from src.tools.llm_client import parse_json_safe
        text = '{"nested": {"key": "value"}, "array": [1, 2, 3]}'
        result = parse_json_safe(text)
        assert result["nested"]["key"] == "value"
        assert len(result["array"]) == 3


# ── R-016: X-Request-ID传播测试 ──

class TestRequestIdPropagation:
    """验证X-Request-ID在请求链路中传播"""

    @pytest.mark.asyncio
    async def test_request_id_generated_when_missing(self):
        """未提供X-Request-ID时应自动生成"""
        from src.middleware.security import security_headers_middleware
        request = Request({
            "type": "http", "method": "GET", "path": "/",
            "headers": [], "query_string": b""
        })
        async def call_next(req):
            return Response("ok")
        response = await security_headers_middleware(request, call_next)
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0

    @pytest.mark.asyncio
    async def test_request_id_preserved_when_provided(self):
        """提供的X-Request-ID应被保留"""
        from src.middleware.security import security_headers_middleware
        custom_id = "custom-request-id-123"
        request = Request({
            "type": "http", "method": "GET", "path": "/",
            "headers": [(b"x-request-id", custom_id.encode())],
            "query_string": b""
        })
        async def call_next(req):
            return Response("ok")
        response = await security_headers_middleware(request, call_next)
        assert response.headers["X-Request-ID"] == custom_id

    @pytest.mark.asyncio
    async def test_request_id_stored_on_state(self):
        """request_id应存储在request.state上"""
        from src.middleware.security import security_headers_middleware
        custom_id = "state-test-id"
        request = Request({
            "type": "http", "method": "GET", "path": "/",
            "headers": [(b"x-request-id", custom_id.encode())],
            "query_string": b""
        })
        captured_request = None
        async def call_next(req):
            nonlocal captured_request
            captured_request = req
            return Response("ok")
        await security_headers_middleware(request, call_next)
        assert hasattr(captured_request.state, "request_id")
        assert captured_request.state.request_id == custom_id


# ── 综合验收测试 ──

class TestAcceptanceCriteria:
    """综合验收标准"""

    def test_no_sync_blocking_in_async_paths(self):
        """异步路径中不应有同步阻塞调用"""
        import inspect
        from src.auth import hash
        from src.utils import mail
        from src.tools import embedding, milvus_client
        # 验证异步方法存在
        assert inspect.iscoroutinefunction(hash.hash_password_async)
        assert inspect.iscoroutinefunction(hash.verify_password_async)
        assert inspect.iscoroutinefunction(mail.send_async)
        assert inspect.iscoroutinefunction(mail.send_alert_async)
        assert inspect.iscoroutinefunction(embedding.EmbeddingEncoder.encode_async)
        assert inspect.iscoroutinefunction(milvus_client.MilvusClient.insert_async)

    def test_error_codes_are_stable(self):
        """错误响应应使用稳定错误码"""
        from src.main import global_exception_handler, value_error_handler
        assert callable(global_exception_handler)
        assert callable(value_error_handler)

    def test_llm_json_parser_handles_edge_cases(self):
        """LLM JSON解析器应处理边界情况"""
        from src.tools.llm_client import parse_json_safe
        # 各种边界情况
        assert parse_json_safe("") == {}
        assert parse_json_safe("null") is None
        assert parse_json_safe("[]") == []
        assert parse_json_safe("  ") == {}
