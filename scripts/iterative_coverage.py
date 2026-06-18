#!/usr/bin/env python3
"""
自迭代知识覆盖引擎 —— 双循环

外循环: coverage_loop()
  → 加载知识地图 → 分析 DB 覆盖率 → 选出缺口概念 → 生成种子 → 进入内循环

内循环: expand_and_generate(seeds)
  → 对种子做 1 轮发散 → L1-L7 去重 → 调用 generate_topic 生成完整内容 → 写库

用法: python3 scripts/iterative_coverage.py --target-coverage 0.75 --max-outer-rounds 5
"""
import sys, json, asyncio, time
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

# ═══════════════════════════════════════════
# 知识地图
# ═══════════════════════════════════════════

MAP_PATH = Path(__file__).resolve().parent / "knowledge_map.json"
CKPT_COVERAGE = Path(__file__).resolve().parent / ".coverage_checkpoint.json"
CKPT_GENERATED = Path(__file__).resolve().parent / ".iter_gen_checkpoint.json"

IMPORTANCE_WEIGHTS = {
    "Java核心": 5, "并发编程": 5, "Spring": 5, "SpringBoot": 5,
    "数据库": 5, "Redis": 5, "JVM": 4, "分布式": 4, "消息队列": 4,
    "系统设计": 4, "SpringCloud": 4, "网络协议": 4,
    "Vue": 3, "前端工程化": 3, "设计模式": 3, "高可用与稳定性": 3,
    "容器化与K8s": 2, "测试": 2, "CICD": 2,
}


def load_map() -> list[dict]:
    with open(MAP_PATH) as f:
        return json.load(f)


# ═══════════════════════════════════════════
# 覆盖率分析
# ═══════════════════════════════════════════

async def analyze_coverage(map_concepts: list[dict]) -> tuple[list, list]:
    """返回 (covered, uncovered) 概念列表"""
    all_topics = await Topic.all()
    topic_texts = [(t.topic, t.keywords or [], t.domain or "") for t in all_topics]

    covered = []
    uncovered = []

    for c in map_concepts:
        name = c["name"]
        matched = False
        for t_name, t_kw, t_domain in topic_texts:
            # 规则1: 精确名包含
            if name in t_name or t_name in name:
                matched = True
                break
            # 规则2: 关键词交集 ≥ 50%
            if t_kw:
                map_words = set(name.replace("与", " ").split())
                kw_words = set(t_kw[:6]) if isinstance(t_kw, list) else set()
                if map_words and kw_words:
                    overlap = len(map_words & kw_words) / min(len(map_words), len(kw_words))
                    if overlap >= 0.4:
                        matched = True
                        break

        if matched:
            covered.append(c)
        else:
            uncovered.append(c)

    return covered, uncovered


# ═══════════════════════════════════════════
# 缺口优先级排序
# ═══════════════════════════════════════════

def rank_gaps(uncovered: list[dict], domain_coverage: dict, batch_size: int = 30) -> list[dict]:
    """
    排序规则：
    1. 领域重要性权重 × (1 - 该领域已有覆盖率)
    2. 同一领域内优先选基础概念（名长短、不用"与"连接的简单概念）
    """
    scored = []
    for c in uncovered:
        domain = c.get("domain", "")
        imp = IMPORTANCE_WEIGHTS.get(domain, 3)
        cov = domain_coverage.get(domain, 0.0)
        gap_score = imp * (1.0 - cov)  # 覆盖率越低的领域优先级越高
        # 简单概念加分（更基础的名 = 更优先）
        name_bonus = 0.3 if "与" not in c["name"] and len(c["name"]) <= 10 else 0
        scored.append((gap_score + name_bonus, c))

    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:batch_size]]


# ═══════════════════════════════════════════
# 内循环：发散 + 生成
# ═══════════════════════════════════════════

async def inner_loop(seeds: list[dict], concurrency: int = 3) -> int:
    """
    内循环：
    1. 对每个种子做 1 轮发散（derivative/extension/prerequisite）
    2. 收集所有新概念（去重后）
    3. 依次生成完整内容并写入 PG
    返回：实际入库数量
    """
    all_names: dict[str, dict] = {}
    for s in seeds:
        all_names[s["name"]] = {"name": s["name"], "domain": s["domain"], "difficulty": 3, "keywords": []}

    # Step 1: 发散 1 轮
    sem = asyncio.Semaphore(concurrency)

    async def expand_one(seed):
        name = seed["name"]
        domain = seed["domain"]
        new_items = []
        for route in ["derivative", "extension", "prerequisite"]:
            async with sem:
                try:
                    fu = await generate_followup(route=route, current_topic_name=name,
                        current_domain=domain, current_difficulty=3, extracted_context={}, persona_level=3)
                    kw_list = fu.get("topic_keywords", [])
                    if kw_list:
                        new_name = kw_list[0] if len(kw_list) == 1 else kw_list[0] + "与" + kw_list[1]
                        new_name = new_name[:50]
                        if new_name not in all_names:
                            new_items.append({"name": new_name, "domain": domain, "difficulty": fu.get("difficulty", 3), "keywords": kw_list})
                except Exception:
                    pass
        return new_items

    print(f"  发散 {len(seeds)} seeds...")
    tasks = [expand_one(s) for s in seeds]
    results = await asyncio.gather(*tasks)
    for items in results:
        for item in items:
            if item["name"] not in all_names:
                all_names[item["name"]] = item

    # Step 2: 去重
    all_topics_list = list(all_names.values())
    completed = load_set(CKPT_GENERATED)
    remaining = [t for t in all_topics_list if t["name"] not in completed]

    print(f"  发散后 {len(all_topics_list)} concepts, 已生成 {len(completed)}, 剩余 {len(remaining)}")

    # Step 3: 逐条生成
    stats = {"generated": 0, "skipped": 0, "failed": 0}
    for batch_start in range(0, len(remaining), 15):
        batch = remaining[batch_start:batch_start + 15]
        batch_results = await asyncio.gather(*[_gen_one(t, sem, stats) for t in batch], return_exceptions=True)

        for r in batch_results:
            if isinstance(r, tuple) and r[1] == "ok":
                completed.add(r[0])
            elif isinstance(r, tuple) and r[1] == "skip":
                completed.add(r[0])

        save_set(CKPT_GENERATED, completed)
        print(f"    [{stats['generated']}/{len(remaining)} gen, {stats['skipped']} skip, {stats['failed']} fail]")
        await asyncio.sleep(2)

    return stats["generated"]


async def _gen_one(t: dict, sem, stats) -> tuple:
    name = t["name"]
    domain = t.get("domain", "通用")
    keywords = t.get("keywords", [])

    async with sem:
        dup = await check_duplicate(name, domain)
        if dup.get("duplicate"):
            stats["skipped"] += 1
            return name, "skip"

        try:
            data = await generate_topic(name, domain, keywords)
        except Exception:
            stats["failed"] += 1
            return name, "fail"

        try:
            slave = SlaveSession(grants=[
                CapabilityRegistry.get("save_to_postgres"),
                CapabilityRegistry.get("save_to_milvus"),
            ])
            state = {"generated_topic": data, "normalized": {"core_concept": name, "domain": domain, "keywords": keywords}}
            await slave.execute(state)
            stats["generated"] += 1
            return name, "ok"
        except Exception:
            stats["failed"] += 1
            return name, "fail"


# ═══════════════════════════════════════════
# 外循环
# ═══════════════════════════════════════════

def load_set(path: Path) -> set:
    if not path.exists(): return set()
    with open(path) as f: return set(json.load(f))


def save_set(path: Path, data: set):
    with open(path, "w") as f: json.dump(list(data), f)


async def outer_loop(target_coverage: float = 0.75, max_rounds: int = 5, batch_size: int = 30, concurrency: int = 3):
    map_concepts = load_map()
    total = len(map_concepts)

    for rnd in range(max_rounds):
        print(f"\n{'='*60}")
        print(f"🔍 OUTER ROUND {rnd+1}/{max_rounds}")
        print(f"{'='*60}")

        # 1. 覆盖率分析
        covered, uncovered = await analyze_coverage(map_concepts)
        cov_pct = len(covered) / total * 100
        domain_cov = defaultdict(lambda: {"total": 0, "covered": 0})
        for c in map_concepts:
            d = c.get("domain", "")
            domain_cov[d]["total"] += 1
        for c in covered:
            domain_cov[c.get("domain", "")]["covered"] += 1
        domain_cov_pct = {d: v["covered"] / max(v["total"], 1) for d, v in domain_cov.items()}

        print(f"  覆盖率: {len(covered)}/{total} ({cov_pct:.1f}%)")
        print(f"  缺口: {len(uncovered)} 个")
        for d, pct in sorted(domain_cov_pct.items(), key=lambda x: x[1]):
            bar = "▓" * int(pct * 10) + "░" * (10 - int(pct * 10))
            print(f"    {d:12s} [{bar}] {pct*100:.0f}%")

        if cov_pct >= target_coverage * 100:
            print(f"\n✅ 达标！覆盖率 {cov_pct:.1f}% >= {target_coverage*100:.0f}%")
            break

        if not uncovered:
            print("\n✅ 全部知识地图已覆盖！")
            break

        # 2. 选出缺口
        seeds = rank_gaps(uncovered, domain_cov_pct, batch_size)
        print(f"\n  本轮种子 ({len(seeds)}):")
        for s in seeds[:10]:
            print(f"    - {s['name']} [{s['domain']}]")
        if len(seeds) > 10:
            print(f"    ... and {len(seeds) - 10} more")

        # 3. 内循环
        print(f"\n  ⚙️ 内循环开始")
        gen_count = await inner_loop(seeds, concurrency)
        print(f"  ⚙️ 内循环完成: +{gen_count} topics")

        # 4. 保存 checkpoint
        save_set(CKPT_COVERAGE, {c["name"] for c in covered})

    final = await Topic.all().count()
    print(f"\n{'='*60}")
    print(f"🏁 COMPLETE: DB has {final} topics")
    print(f"{'='*60}")


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-coverage", type=float, default=0.75)
    parser.add_argument("--max-outer-rounds", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--concurrency", type=int, default=2)
    args = parser.parse_args()

    await init_db()
    register_all()

    await outer_loop(args.target_coverage, args.max_outer_rounds, args.batch_size, args.concurrency)
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
