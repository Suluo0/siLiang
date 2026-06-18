"""API 全链路测试 —— 只调 POST /api/topic/generate，不包含任何业务逻辑"""
import httpx
import asyncio

API = "http://127.0.0.1:8000/api/topic/generate"

TESTS = [
    "HashMap底层实现",
    "ConcurrentHashMap原理",
    "MySQL索引原理",
]


async def main():
    async with httpx.AsyncClient() as c:
        for t in TESTS:
            resp = await c.post(API, json={"user_input": t}, timeout=120)
            data = resp.json()
            ok = "✅" if data.get("success") else "❌"
            print(f"{ok} {t:30s} | {data.get('source','?'):10s} | topic={data.get('topic_name','N/A')} | {data.get('trace_id','')[:8]}")
            if not data.get("success"):
                print(f"   error: {data.get('message','')[:100]}")

asyncio.run(main())
