"""R-008 browser security header regression tests."""
import pytest
from starlette.requests import Request
from starlette.responses import Response

from src.middleware.security import security_headers_middleware

pytestmark = [pytest.mark.unit, pytest.mark.security]


def _request(scheme: str = "http") -> Request:
    return Request({
        "type": "http", "method": "GET", "path": "/", "headers": [],
        "scheme": scheme, "server": ("test", 443 if scheme == "https" else 80),
        "query_string": b"",
    })


@pytest.mark.asyncio
async def test_security_headers_block_inline_scripts_and_frames():
    async def call_next(_request):
        return Response("ok")

    response = await security_headers_middleware(_request(), call_next)
    csp = response.headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp
    assert "unsafe-inline" not in csp.split("script-src", 1)[1].split(";", 1)[0]
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.asyncio
async def test_hsts_is_only_emitted_for_https():
    async def call_next(_request):
        return Response("ok")

    insecure = await security_headers_middleware(_request("http"), call_next)
    secure = await security_headers_middleware(_request("https"), call_next)
    assert "Strict-Transport-Security" not in insecure.headers
    assert secure.headers["Strict-Transport-Security"].startswith("max-age=31536000")
