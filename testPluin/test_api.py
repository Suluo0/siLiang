#!/usr/bin/env python3
"""
API 全接口自动化测试
用法: python testPluin/test_api.py
环境变量:
  BASE_URL  - API 地址 (默认 http://localhost:8000)
  SKIP_AUTH - 跳过鉴权接口测试 (默认 False)
"""
import os, sys, json, time, traceback
from dataclasses import dataclass
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")


@dataclass
class Result:
    endpoint: str
    method: str
    status: int
    passed: bool
    latency_ms: float
    error: str = ""


def call(method: str, path: str, body: dict = None, token: str = None,
         raw: bool = False) -> tuple[int, dict | str, float]:
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None

    t0 = time.time()
    req = Request(url, data=data, headers=headers, method=method)
    try:
        resp = urlopen(req, timeout=15)
        status = resp.code
        body_raw = resp.read().decode()
        try:
            body_json = json.loads(body_raw) if body_raw.strip() else {}
            return status, body_json, (time.time() - t0) * 1000
        except json.JSONDecodeError:
            return status, body_raw[:200], (time.time() - t0) * 1000
    except HTTPError as e:
        body_raw = e.read().decode()
        try:
            return e.code, json.loads(body_raw), (time.time() - t0) * 1000
        except json.JSONDecodeError:
            return e.code, body_raw[:200], (time.time() - t0) * 1000
    except URLError as e:
        return 0, {"error": str(e.reason)}, (time.time() - t0) * 1000


def test(label: str, method: str, path: str, expected: int,
         token: str = None, body: dict = None) -> Result:
    status, resp, ms = call(method, path, body, token)
    passed = status == expected
    err = ""
    if not passed:
        if isinstance(resp, dict):
            err = resp.get("detail", resp.get("error", str(resp)[:100]))
        else:
            err = str(resp)[:100]
    return Result(f"{method} {path}", label, status, passed, ms, err)


def run():
    print(f"═══════════════════════════════════")
    print(f"  API 全接口测试 — {BASE_URL}")
    print(f"═══════════════════════════════════\n")
    results: list[Result] = []

    # ═══════════════ Phase 1: Public ═══════════════
    print("─ Phase 1: 公开端点 ─")
    for r in [
        test("健康检查", "GET", "/ping", 200),
        test("API docs", "GET", "/docs", 200),
        test("OpenAPI JSON", "GET", "/openapi.json", 200),
        test("Root", "GET", "/", 200),
        test("Tags", "GET", "/api/v1/topic/tags", 200),
    ]:
        mark = "✅" if r.passed else "❌"
        print(f"  {mark} {r.endpoint} → {r.status} ({r.latency_ms:.0f}ms)" +
              (f" — {r.error}" if not r.passed else ""))
        results.append(r)

    # ═══════════════ Phase 2: Auth ═══════════════
    print("\n─ Phase 2: 鉴权 ─")
    test_email = f"apitest_{int(time.time()*1000)}@test.com"
    test_pw = "Test1234"

    # Register
    r = test("注册", "POST", "/api/auth/register", 200, body={
        "username": f"test_{int(time.time()*1000)}", "email": test_email, "password": test_pw
    })
    mark = "✅" if r.passed else "⚠️"
    print(f"  {mark} {r.endpoint} → {r.status}" + (f" (已存在)" if r.status == 409 else ""))
    results.append(r)

    # Login
    r_login = call("POST", "/api/auth/login", body={"email": test_email, "password": test_pw})
    token = r_login[1].get("access_token", "") if isinstance(r_login[1], dict) else ""
    r = Result("POST /api/auth/login", "登录", r_login[0], r_login[0] == 200,
               r_login[2], "" if token else "未获取到 token")
    mark = "✅" if r.passed else "❌"
    print(f"  {mark} {r.endpoint} → {r.status}" + (f" — {r.error}" if not r.passed else ""))
    results.append(r)

    if not token:
        print("\n⚠️  未获取到 token，跳过鉴权接口测试")
        return results

    # Refresh — use token from login response
    r_data = call("POST", "/api/auth/login", body={"email": test_email, "password": test_pw})[1]
    refresh = r_data.get("refresh_token", "") if isinstance(r_data, dict) else ""
    token = r_data.get("access_token", "") if isinstance(r_data, dict) else ""
    r = test("刷新 token", "POST", "/api/auth/refresh", 200, body={"refresh_token": refresh})
    mark = "✅" if r.passed else "❌"
    print(f"  {mark} {r.endpoint} → {r.status}")
    results.append(r)

    # Me
    r = test("个人信息", "GET", "/api/auth/me", 200, token=token)
    mark = "✅" if r.passed else "❌"
    print(f"  {mark} {r.endpoint} → {r.status}" + (f" — {r.error}" if not r.passed else ""))
    results.append(r)

    # ═══════════════ Phase 3: Topic (authed) ═══════════════
    print("\n─ Phase 3: 题库 (鉴权) ─")
    for r in [
        test("列表", "GET", "/api/v1/topic/list?limit=2", 200, token=token),
    ]:
        mark = "✅" if r.passed else "❌"
        print(f"  {mark} {r.endpoint} → {r.status}" +
              (f" — {r.error}" if not r.passed else ""))
        results.append(r)

    # Topic detail (use the first topic ID)
    r_list = call("GET", "/api/v1/topic/list?limit=1", token=token)
    items = r_list[1].get("items", []) if isinstance(r_list[1], dict) else []
    if items:
        tid = items[0]["id"]
        r = test("详情", "GET", f"/api/v1/topic/{tid}", 200, token=token)
    else:
        r = Result("GET /api/v1/topic/:id", "详情", 0, False, 0, "无可用 ID")
    mark = "✅" if r.passed else "❌"
    print(f"  {mark} {r.endpoint} → {r.status}" +
          (f" — {r.error}" if not r.passed else ""))
    results.append(r)

    # ═══════════════ Phase 4: Agent ═══════════════
    print("\n─ Phase 4: Agent 对话 ─")
    r = test("v3 生成", "POST", "/api/v3/topic/generate", 200, token=token,
             body={"user_input": "HashMap"})
    mark = "✅" if r.passed else "⚠️"
    print(f"  {mark} {r.endpoint} → {r.status}" +
          (f" — {r.error[:60]}" if not r.passed else f" ({r.latency_ms:.0f}ms)"))

    # ═══════════════ 401 验证 ═══════════════
    print("\n─ Phase 5: 鉴权阻断验证 ─")
    for r in [
        test("无token列表", "GET", "/api/v1/topic/list?limit=1", 401),
        test("无token详情", "GET", "/api/v1/topic/xxx", 401),
    ]:
        mark = "✅" if r.passed else "❌"
        print(f"  {mark} {r.endpoint} → {r.status}")
        results.append(r)

    # ═══════════════ 总结 ═══════════════
    print(f"\n══════════════════════════")
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"  {passed}/{total} 通过" + (" ✅" if passed == total else f" ({total-passed} failed)"))
    print(f"══════════════════════════")
    return results


if __name__ == "__main__":
    run()
