#!/usr/bin/env python3
"""
长任务生成器 —— 单次补充 300+ 题目，持续循环直到达标或缺口填满

策略：
1. 加载 knowledge_map.json → 分析 DB 覆盖率 → 选出缺口
2. 按领域优先级排序（覆盖率越低的领域越优先）
3. 取缺口概念作为种子，做 1 轮发散
4. 逐条生成完整内容（并发 3，checkpoint 每 10 条）
5. 循环直到：DB 增长 ≥ target  OR  缺口耗光
6. 断点续传：crash 后重启自动从 checkpoint 继续

用法：
  python3 scripts/long_run_gen.py --target 300 --concurrency 3
  nohup python3 scripts/long_run_gen.py --target 300 --concurrency 3 > /tmp/long_run.log 2>&1 &
"""
import sys, json, asyncio, time, signal, os
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.database import init_db, close_db
from src.agentv3.capabilities.register import register_all
from src.agentv3.capabilities.duplicate import check_duplicate
from src.agentv3.capabilities.generate import generate_topic
from src.agentv3.capabilities.generate_followup import generate_followup
from src.agentv3.registry import CapabilityRegistry
from src.agentv3.slave import SlaveSession
from src.models import Topic

# ── 配置 ──
MAP_PATH = Path(__file__).resolve().parent / "knowledge_map.json"
CKPT_PATH = Path(__file__).resolve().parent / ".long_run_ckpt.json"
GAP_CACHE_PATH = Path(__file__).resolve().parent / ".long_run_gaps.json"
LOG_PATH = Path(__file__).resolve().parent / ".long_run_progress.log"
BATCH_SIZE = 20
CHECKPOINT_EVERY = 10

# ── 全局状态 ──
shutting_down = False
stats = {"generated": 0, "skipped": 0, "failed": 0, "total_attempts": 0}


def load_json(path: Path, default=None):
    if not path.exists(): return default if default is not None else {}
    with open(path) as f: return json.load(f)


def save_json(path: Path, data):
    with open(path, "w") as f: json.dump(data, f, ensure_ascii=False)


def load_map():
    with open(MAP_PATH) as f: return json.load(f)


def log(msg: str):
    timestamp = time.strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f: f.write(line + "\n")


# ── 覆盖率分析 ──
async def analyze_gaps() -> list[dict]:
    """返回未覆盖概念列表，按领域覆盖率优先级排序"""
    all_concepts = load_map()
    all_topics = await Topic.all()
    topic_texts = [(t.topic, t.keywords or [], t.domain or "") for t in all_topics]

    domain_total = defaultdict(int)
    domain_cov = defaultdict(int)
    uncovered = []

    for c in all_concepts:
        name = c["name"]
        domain = c.get("domain", "")
        domain_total[domain] += 1
        matched = False
        for t_name, t_kw, t_domain in topic_texts:
            if name in t_name or t_name in name:
                matched = True; break
            if t_kw:
                mw = set(name.replace("与"," ").split())
                kw = set((t_kw or [])[:6])
                if mw and kw and len(mw & kw) / min(len(mw), len(kw)) >= 0.4:
                    matched = True; break
        if matched:
            domain_cov[domain] += 1
        else:
            uncovered.append(c)

    # 领域覆盖率
    domain_pct = {d: domain_cov[d] / max(domain_total[d], 1) for d in domain_total}

    # 按缺口分数排序：高重要性 × 低覆盖率
    importance = {"数据库":5,"Java核心":5,"并发编程":5,"Spring":5,"Redis":5,"MyBatis":5,
                  "Sentinel":5,"Seata":5,"Nacos":5,"Nginx":5,"RocketMQ":5,"Dubbo":5,
                  "JVM":4,"分布式":4,"消息队列":4,"SpringCloud":4,"Netty":4,
                  "ElasticSearch":4,"ZooKeeper":4,"ShardingSphere":4,"SkyWalking":4,
                  "Prometheus":4,"SpringBoot":3,"Vue":3,"设计模式":3,"高可用与稳定性":3,
                  "容器化与K8s":2,"定时任务":2,"测试":2,"CICD":2,"软件工程":2,"Linux":2}

    scored = []
    for c in uncovered:
        d = c.get("domain", "")
        imp = importance.get(d, 3)
        cov = domain_pct.get(d, 1.0)
        gap_score = imp * (1.0 - cov)
        scored.append((gap_score, c))
    scored.sort(key=lambda x: -x[0])

    return [c for _, c in scored]


# ── 发散一个种子 ──
async def expand_one_seed(seed: dict, sem, all_names: set) -> list[dict]:
    """对种子做 3 方向发散，返回新概念列表"""
    name = seed["name"]
    domain = seed.get("domain", "通用")
    new_items = []
    for route in ["derivative", "extension", "prerequisite"]:
        async with sem:
            try:
                fu = await generate_followup(
                    route=route, current_topic_name=name,
                    current_domain=domain, current_difficulty=3,
                    extracted_context={}, persona_level=3)
                kw = fu.get("topic_keywords", [])
                if kw:
                    nn = kw[0] if len(kw) == 1 else kw[0] + "与" + kw[1]
                    nn = nn[:50]
                    if nn not in all_names:
                        all_names.add(nn)
                        new_items.append({"name": nn, "domain": domain,
                                          "difficulty": fu.get("difficulty", 3),
                                          "keywords": kw})
            except Exception:
                pass
    return new_items


# ── 生成一条 ──
async def gen_one(item: dict, sem) -> tuple:
    """生成完整内容 + 写入 PG/Milvus"""
    name = item["name"]
    domain = item.get("domain", "通用")
    keywords = item.get("keywords", [])

    async with sem:
        dup = await check_duplicate(name, domain)
        if dup.get("duplicate"):
            stats["skipped"] += 1
            return "skip"

        for retry in range(3):
            try:
                data = await generate_topic(name, domain, keywords)
                slave = SlaveSession(grants=[
                    CapabilityRegistry.get("save_to_postgres"),
                    CapabilityRegistry.get("save_to_milvus")])
                state = {"generated_topic": data,
                         "normalized": {"core_concept": name, "domain": domain, "keywords": keywords}}
                await slave.execute(state)
                stats["generated"] += 1
                return "ok"
            except Exception as e:
                if retry < 2:
                    await asyncio.sleep(2 ** retry)  # 指数退避
                else:
                    stats["failed"] += 1
                    log(f"  FAIL(retries exhausted): {name[:50]} — {str(e)[:80]}")
                    return "fail"


# ── 主循环 ──
async def main_loop(target: int, concurrency: int):
    global shutting_down

    def handle_signal(sig, frame):
        global shutting_down
        shutting_down = True
        log(f"SIGNAL {sig} received, shutting down gracefully...")
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    await init_db()
    register_all()
    sem = asyncio.Semaphore(concurrency)

    initial_count = await Topic.all().count()
    target_count = initial_count + target
    checkpoint = load_json(CKPT_PATH, {"done": []})
    done_names = set(checkpoint.get("done", []))

    log(f"═══ LONG RUN GEN START ═══")
    log(f"  DB start: {initial_count} topics")
    log(f"  Target: {target_count} (+{target})")
    log(f"  Concurrency: {concurrency}")
    log(f"  Checkpoint: {len(done_names)} already done")

    # ── 间隙分析 ──
    log("  Analyzing gaps...")
    gaps = await analyze_gaps()
    log(f"  Total gaps: {len(gaps)}")

    # 只取未完成的 gaps
    remaining_gaps = [g for g in gaps if g["name"] not in done_names]

    round_idx = 0
    while not shutting_down:
        db_now = await Topic.all().count()
        added = db_now - initial_count
        if added >= target or not remaining_gaps:
            log(f"  TARGET REACHED: DB={db_now}, added={added}")
            break

        round_idx += 1
        batch_size = min(BATCH_SIZE, len(remaining_gaps))
        batch = remaining_gaps[:batch_size]
        remaining_gaps = remaining_gaps[batch_size:]

        log(f"\n  ROUND {round_idx}: {len(batch)} gaps, DB={db_now} (+{added}/{target}), skip={stats['skipped']}")

        # ── Step 1: 发散 ──
        all_names = set()
        for b in batch:
            all_names.add(b["name"])
        expanded = []
        for i in range(0, len(batch), max(1, concurrency)):
            sub = batch[i:i + concurrency]
            results = await asyncio.gather(*[expand_one_seed(s, sem, all_names) for s in sub])
            for r in results:
                expanded.extend(r)

        unique = [x for x in expanded if x["name"] not in done_names]
        log(f"    Expanded: {len(expanded)} concepts, {len(unique)} new")

        # ── Step 2: 生成 ──
        if not unique:
            # 发散无新概念 → 直接生成 gaps 本身
            log(f"    No new concepts from expand, generating gaps directly")
            unique = batch

        gen_batch = unique
        for bi in range(0, len(gen_batch), concurrency):
            sub = gen_batch[bi:bi + concurrency]
            results = await asyncio.gather(*[gen_one(x, sem) for x in sub])
            for r in results:
                if isinstance(r, str) and r in ("ok", "skip"):
                    # find the name
                    pass  # gen_one already updated stats

            # checkpoint: mark attempted items as done
            for x in sub:
                done_names.add(x["name"])
            save_json(CKPT_PATH, {"done": list(done_names)})

            if (bi // concurrency + 1) % 3 == 0:
                db_now = await Topic.all().count()
                added = db_now - initial_count
                log(f"    Progress: DB={db_now} (+{added}), gen={stats['generated']}, skip={stats['skipped']}")
                if added >= target:
                    break

            await asyncio.sleep(2)  # rate limit

        if shutting_down:
            break

    final = await Topic.all().count()
    added = final - initial_count
    log(f"\n═══ LONG RUN GEN DONE ═══")
    log(f"  DB final: {final} (+{added})")
    log(f"  Generated: {stats['generated']}, Skipped: {stats['skipped']}, Failed: {stats['failed']}")
    save_json(CKPT_PATH, {"done": list(done_names)})
    await close_db()


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=300)
    parser.add_argument("--concurrency", type=int, default=3)
    args = parser.parse_args()
    await main_loop(args.target, args.concurrency)


if __name__ == "__main__":
    asyncio.run(main())
