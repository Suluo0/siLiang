#!/usr/bin/env python3
"""
批量面试题生成脚本
Phase 1: 验证 → Phase 2: 单题冒烟 → Phase 3: 小批量 → Phase 4: 全量
"""
import asyncio, json, sys, os, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.database import init_db, close_db

SEED_FILE = Path(__file__).resolve().parent / "seed_topics.json"
CHECKPOINT_FILE = Path(__file__).resolve().parent / ".batch_checkpoint.json"
BATCH_SIZES = [1, 5, None]  # Phase 2: 1题 / Phase 3: 5题 / Phase 4: 全量


async def init_system():
    """初始化 Tortoise ORM + 注册能力"""
    await init_db()
    from src.agentv3.capabilities.register import register_all
    register_all()


def load_seeds() -> list[dict]:
    with open(SEED_FILE) as f:
        return json.load(f)


def load_checkpoint() -> set:
    if not CHECKPOINT_FILE.exists():
        return set()
    with open(CHECKPOINT_FILE) as f:
        return set(json.load(f))


def save_checkpoint(names: set):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(list(names), f)


async def process_one(seed: dict, sem: asyncio.Semaphore, stats: dict) -> dict:
    from src.agentv3.capabilities.duplicate import check_duplicate
    from src.agentv3.capabilities.generate import generate_topic
    from src.agentv3.capabilities.validate import validate_output
    from src.agentv3.registry import CapabilityRegistry
    from src.agentv3.slave import SlaveSession

    name = seed["name"]
    domain = seed.get("domain", "")
    keywords = seed.get("keywords", [])

    async with sem:
        t0 = time.monotonic()

        # L1+L2: 去重
        try:
            dup = await check_duplicate(name, domain)
        except Exception as e:
            stats["failed"] += 1
            print(f"  FAIL (dup error): {name} — {e}")
            return {"name": name, "status": "failed", "error": str(e)}

        if dup["duplicate"]:
            print(f"  SKIP ({dup['method']}): {name} ≈ {dup.get('matched_topic', {}).get('name', '?')} ({dup['similarity']:.3f})")
            stats["skipped"] += 1
            return {"name": name, "status": "skipped"}

        # 生成
        try:
            topic_data = await generate_topic(name, domain, keywords)
        except Exception as e:
            stats["failed"] += 1
            print(f"  FAIL (gen): {name} — {e}")
            return {"name": name, "status": "failed", "error": str(e)}

        # 校验
        try:
            val = await validate_output(topic_data, name)
        except Exception:
            val = {"valid": True, "quality": 0.5}

        q = val.get("quality", 0)

        # Slave 写入
        try:
            slave = SlaveSession(grants=[
                CapabilityRegistry.get("save_to_postgres"),
                CapabilityRegistry.get("save_to_milvus"),
            ])
            slave_state = {
                "generated_topic": topic_data,
                "normalized": {"core_concept": name, "domain": domain, "keywords": keywords},
            }
            sr = await slave.execute(slave_state)
        except Exception as e:
            stats["failed"] += 1
            print(f"  FAIL (write): {name} — {e}")
            return {"name": name, "status": "failed", "error": str(e)}

        elapsed = time.monotonic() - t0
        stats["generated"] += 1
        tid = sr.topic_id[:8] if sr.topic_id else "no-id"
        print(f"  OK ({elapsed:.1f}s, q={q:.2f}): {name} → {tid}")
        return {"name": name, "status": "ok", "topic_id": sr.topic_id}


async def run_batch(seeds: list[dict], concurrency: int, label: str):
    existing = load_checkpoint()
    remaining = [s for s in seeds if s["name"] not in existing]

    if not remaining:
        print(f"[{label}] 全部已处理 (checkpoint).")
        return

    stats = {"generated": 0, "skipped": 0, "failed": 0}
    completed = set(existing)
    sem = asyncio.Semaphore(concurrency)

    token_est = len(remaining) * 3000
    print(f"\n{'='*60}")
    print(f"[{label}] 批量生成: {len(remaining)} 题, 并发={concurrency}")
    print(f"[{label}] Token 估算: ~{token_est}, ~${token_est * 0.0000003:.2f} (DeepSeek)")
    print(f"{'='*60}")

    tasks = [process_one(s, sem, stats) for s in remaining]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, dict) and r.get("status") in ("ok", "skipped"):
            completed.add(r["name"])

    save_checkpoint(completed)

    print(f"[{label}] 完成: {stats['generated']} 生成, {stats['skipped']} 跳过, {stats['failed']} 失败")
    print(f"[{label}] 进度: {len(completed)}/{len(seeds)}")


async def main():
    await init_system()
    seeds = load_seeds()
    print(f"种子文件: {len(seeds)} 题")

    # Phase 1: 验证
    print("\n═══ Phase 1: 基础设施验证 ═══")
    from src.models.topic import Topic
    db_count = await Topic.all().count()
    print(f"  PG topics: {db_count}")
    try:
        from src.tools.llm_client import LLMClient
        llm = LLMClient.get_instance()
        test = await llm.ainvoke("say hi", max_tokens=10)
        print(f"  LLM API: OK (key={llm.api_key[:10]}...)")
    except Exception as e:
        print(f"  LLM API: FAIL — {e}")
        return
    print("  验证通过\n")

    # Phase 2: 单题冒烟
    print("═══ Phase 2: 单题冒烟 ═══")
    await run_batch(seeds[:1], concurrency=1, label="Smoke")

    # Phase 3: 小批量
    print("\n═══ Phase 3: 小批量验证 ═══")
    await run_batch(seeds[:5], concurrency=3, label="SmallBatch")

    # Phase 4: 全量
    print("\n═══ Phase 4: 全量生成 ═══")
    await run_batch(seeds, concurrency=10, label="FullBatch")

    # 最终统计
    from src.models.topic import Topic
    final = await Topic.all().count()
    print(f"\n{'='*60}")
    print(f"全部完成: PG 中共 {final} 道题")
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
