#!/usr/bin/env python3
"""
API 全接口测试 (v2 — 支持 CAPTCHA 流程)
用法: python3 testPluin/test_api.py
"""
import os, sys, json, time
from dataclasses import dataclass
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")


@dataclass
class Result:
    endpoint: str; label: str; status: int; passed: bool
    latency_ms: float; error: str = ""


def call(method: str, path: str, body: dict = None, token: str = None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    t0 = time.time()
    try:
        resp = urlopen(Request(url, data=data, headers=headers, method=method), timeout=15)
        raw = resp.read().decode()
        try: j = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError: j = raw[:200]
        return resp.code, j, (time.time()-t0)*1000
    except HTTPError as e:
        raw = e.read().decode()
        try: j = json.loads(raw)
        except json.JSONDecodeError: j = raw[:200]
        return e.code, j, (time.time()-t0)*1000
    except URLError as e:
        return 0, {"error": str(e.reason)}, (time.time()-t0)*1000


def test(label, method, path, expected, token=None, body=None) -> Result:
    status, resp, ms = call(method, path, body, token)
    passed = status == expected
    err = resp.get("detail", str(resp)[:100]) if isinstance(resp, dict) else str(resp)[:100] if not passed else ""
    return Result(f"{method} {path}", label, status, passed, ms, err)


def run():
    print(f"═══ API Test — {BASE_URL} ═══\n")
    results = []

    # Phase 1: Public
    print("─ Phase 1: Public ─")
    for r in [test("ping","GET","/ping",200), test("docs","GET","/docs",200),
              test("openapi","GET","/openapi.json",200), test("root","GET","/",200),
              test("tags","GET","/api/v1/topic/tags",200), test("captcha","GET","/api/auth/captcha",200)]:
        print(f"  {'✅' if r.passed else '❌'} {r.endpoint} → {r.status} ({r.latency_ms:.0f}ms)" +
              (f" — {r.error}" if not r.passed else ""))
        results.append(r)

    # Phase 2: Auth with CAPTCHA (using pre-existing user "qw")
    print("\n─ Phase 2: Auth (CAPTCHA) ─")
    pw = "123456"

    # Captcha
    cl = call("GET","/api/auth/captcha")
    cid, ccode = (cl[1].get("captcha_id"), cl[1].get("captcha_text")) if isinstance(cl[1], dict) else ("","")

    # Login
    rl = call("POST","/api/auth/login",body={"username":"qw","password":pw,
                "captcha_id":cid,"captcha_answer":ccode})
    token = rl[1].get("access_token","") if isinstance(rl[1], dict) else ""
    r = Result("POST /api/auth/login","login",rl[0],rl[0]==200,rl[2],"" if token else "no token")
    print(f"  {'✅' if r.passed else '❌'} {r.endpoint} → {r.status}" + (f" — {r.error}" if not r.passed else ""))
    results.append(r)

    if not token:
        print("  ⚠️  no token → skip authed tests")
        _summary(results); return

    # Refresh
    refresh = rl[1].get("refresh_token","") if isinstance(rl[1], dict) else ""
    r = test("refresh","POST","/api/auth/refresh",200,body={"refresh_token":refresh})
    print(f"  {'✅' if r.passed else '❌'} {r.endpoint} → {r.status}" + (f" — {r.error}" if not r.passed else ""))
    results.append(r)

    # Send-code (CAPTCHA + email flow smoke test)
    csc = call("GET","/api/auth/captcha")
    cid_sc, ccode_sc = (csc[1].get("captcha_id"), csc[1].get("captcha_text")) if isinstance(csc[1], dict) else ("","")
    r = test("send-code","POST","/api/auth/send-code",200,body={
        "email": f"smoke_{int(time.time()*1000)}@t.com", "captcha_id": cid_sc, "captcha_answer": ccode_sc
    })
    print(f"  {'✅' if r.passed else '⚠️'} {r.endpoint} → {r.status}" + (f" — {r.error}" if not r.passed else ""))
    results.append(r)

    # Me
    r = test("me","GET","/api/auth/me",200,token=token)
    print(f"  {'✅' if r.passed else '❌'} {r.endpoint} → {r.status}")
    results.append(r)

    # Phase 3: Topic
    print("\n─ Phase 3: Topic ─")
    for r in [test("list","GET","/api/v1/topic/list?limit=2",200,token=token)]:
        print(f"  {'✅' if r.passed else '❌'} {r.endpoint} → {r.status}")
        results.append(r)

    # Detail
    rl2 = call("GET","/api/v1/topic/list?limit=1",token=token)
    items = rl2[1].get("items",[]) if isinstance(rl2[1],dict) else []
    tid = items[0]["id"] if items else "none"
    r = test("detail", "GET", f"/api/v1/topic/{tid}", 200, token=token)
    print(f"  {'✅' if r.passed else '❌'} {r.endpoint} → {r.status}")
    results.append(r)

    # Phase 4: Agent
    print("\n─ Phase 4: Agent ─")
    r = test("v3gen","POST","/api/v3/topic/generate",200,token=token,body={"user_input":"HashMap"})
    m = "✅" if r.passed else f"⚠️ {r.status} ({r.latency_ms:.0f}ms)"
    print(f"  {m} {r.endpoint}")

    # Phase 5: Block
    print("\n─ Phase 5: 401 ─")
    for r in [test("noauth","GET","/api/v1/topic/list?limit=1",401),
              test("badid","GET","/api/v1/topic/xxx",401)]:
        print(f"  {'✅' if r.passed else '❌'} {r.endpoint} → {r.status}")
        results.append(r)

    _summary(results)


def _summary(results):
    p = sum(1 for r in results if r.passed)
    t = len(results)
    print(f"\n═══ {p}/{t} passed {'✅' if p==t else ''} ═══")


if __name__ == "__main__":
    run()
