"""R-002 验证码泄露与存储安全单元测试。"""
import base64

import pytest

from src.auth.api import _generate_captcha_image
from src.models.captcha import hash_verification_code

pytestmark = [pytest.mark.unit, pytest.mark.security]


def test_captcha_is_png_data_uri_without_plaintext():
    value = _generate_captcha_image("1234")
    assert value.startswith("data:image/png;base64,")
    payload = base64.b64decode(value.split(",", 1)[1])
    assert payload.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"1234" not in payload


def test_hash_is_bound_to_purpose_and_target():
    base = hash_verification_code("654321", "email", "a@example.com")
    assert base != "654321"
    assert base != hash_verification_code("654321", "email", "b@example.com")
    assert base != hash_verification_code("654321", "captcha", "a@example.com")
