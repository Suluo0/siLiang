#!/usr/bin/env python3
"""
智能题目发散生成脚本 —— 利用 generate_followup 能力树状发散
从一个核心概念出发，衍生/扩展/前置三个方向层层展开，凑齐足够面试题

原理：
  Step 1: 从核心种子出发
  Step 2: 对每个种子调用 generate_followup(derivative/extension/prerequisite)
  Step 3: 收集返回的 topic_keywords 作为新种子
  Step 4: 去重、递归 N 轮
  Step 5: 对全部种子调用 generate_topic + slave 写入生成完整内容

用法: python3 scripts/expand_topics.py --rounds 3 --concurrency 3
"""
import asyncio, json, time, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.database import init_db, close_db
from src.agentv3.capabilities.register import register_all
from src.agentv3.capabilities.generate_followup import generate_followup
from src.agentv3.capabilities.generate import generate_topic
from src.agentv3.capabilities.duplicate import check_duplicate
from src.agentv3.registry import CapabilityRegistry
from src.agentv3.slave import SlaveSession

# ═══════════════════════════════════════════
# 核心种子 —— 从各领域各取 2-3 个代表性概念
# ═══════════════════════════════════════════

CORE_SEEDS = [
    # Java 核心
    {"concept": "面向对象三大特性", "domain": "Java核心", "keywords": ["封装", "继承", "多态"]},
    {"concept": "Java异常处理机制", "domain": "Java核心", "keywords": ["try-catch", "throw", "异常链"]},
    {"concept": "Java反射机制", "domain": "Java核心", "keywords": ["Class", "Method", "动态代理"]},

    # 集合
    {"concept": "HashMap底层实现", "domain": "Java集合", "keywords": ["哈希表", "红黑树", "扰动函数"]},
    {"concept": "ConcurrentHashMap原理", "domain": "Java集合", "keywords": ["CAS", "分段锁", "线程安全"]},

    # 并发
    {"concept": "synchronized锁升级过程", "domain": "并发编程", "keywords": ["偏向锁", "轻量级锁", "重量级锁"]},
    {"concept": "线程池原理与调优", "domain": "并发编程", "keywords": ["核心线程", "拒绝策略", "keepAlive"]},
    {"concept": "AQS原理与ReentrantLock", "domain": "并发编程", "keywords": ["AQS", "CLH队列", "公平锁"]},

    # JVM
    {"concept": "JVM垃圾回收机制", "domain": "JVM", "keywords": ["GC", "CMS", "G1", "STW"]},
    {"concept": "JVM类加载机制", "domain": "JVM", "keywords": ["双亲委派", "Bootstrap", "破坏委托"]},

    # Spring
    {"concept": "Spring IoC容器原理", "domain": "Spring", "keywords": ["IoC", "DI", "BeanFactory"]},
    {"concept": "Spring AOP实现机制", "domain": "Spring", "keywords": ["动态代理", "CGLIB", "切面"]},
    {"concept": "Spring事务管理", "domain": "Spring", "keywords": ["事务传播", "隔离级别", "@Transactional"]},

    # 数据库
    {"concept": "MySQL索引原理与优化", "domain": "数据库", "keywords": ["B+树", "覆盖索引", "回表"]},
    {"concept": "MySQL事务与MVCC", "domain": "数据库", "keywords": ["MVCC", "隔离级别", "ReadView"]},

    # Redis
    {"concept": "Redis数据结构与缓存策略", "domain": "缓存", "keywords": ["SDS", "skiplist", "缓存穿透"]},
    {"concept": "Redis集群与高可用", "domain": "缓存", "keywords": ["Cluster", "Sentinel", "故障转移"]},

    # 消息队列
    {"concept": "Kafka消息可靠性机制", "domain": "消息队列", "keywords": ["ISR", "ACK", "幂等"]},

    # 分布式
    {"concept": "CAP理论与BASE理论", "domain": "分布式", "keywords": ["CAP", "最终一致性", "分区容错"]},
    {"concept": "分布式事务解决方案", "domain": "分布式", "keywords": ["Seata", "TCC", "SAGA"]},

    # 系统设计
    {"concept": "秒杀系统设计", "domain": "系统设计", "keywords": ["限流", "库存", "异步"]},
    {"concept": "短链接系统设计", "domain": "系统设计", "keywords": ["哈希", "Base62", "重定向"]},

    # Vue
    {"concept": "Vue3响应式原理", "domain": "Vue", "keywords": ["Proxy", "Reflect", "响应式"]},
    {"concept": "Vue组件通信方式", "domain": "Vue", "keywords": ["props", "emit", "provide", "inject"]},
]

# ═══════════════════════════════════════════
# Step 1: 发散 Topic 概念
# ═══════════════════════════════════════════

CHECKPOINT_EXPAND = Path(__file__).resolve().parent / ".expand_checkpoint.json"
CHECKPOINT_GEN = Path(__file__).resolve().parent / ".gen_checkpoint.json"


def load_set(path: Path) -> set:
    if not path.exists():
        return set()
    with open(path) as f:
        return set(json.load(f))


def save_set(path: Path, data: set):
    with open(path, "w") as f:
        json.dump(list(data), f)


# ═══════════════════════════════════════════
# 去重防呆规则（嵌入 expand 流程）
# ═══════════════════════════════════════════

_STRIP_SUFFIXES = [
    "——源码分析", "——底层原理", "——实战案例", "——最佳实践",
    "——常见面试题解答", "——性能优化方案", "——生产环境踩坑记录",
    "——设计思想与演进", "源码分析", "底层原理", "最佳实践",
]


def _normalize_name(name: str) -> str:
    """标准化题目名——去掉变体后缀"""
    n = name.strip()
    for sfx in _STRIP_SUFFIXES:
        if n.endswith(sfx):
            n = n[:-len(sfx)].strip()
            break
    return n


def _is_too_similar(new_name: str, existing: dict[str, dict]) -> bool:
    """检查新名是否与已有集合中任一题目高度相似"""
    norm_new = _normalize_name(new_name)
    for key in existing:
        norm_ex = _normalize_name(key)
        # 规则1: 子串包含
        if norm_new in norm_ex or norm_ex in norm_new:
            return True
        # 规则2: 共享词 ≥70%
        ws1 = set(norm_new.replace("与", " ").split())
        ws2 = set(norm_ex.replace("与", " ").split())
        if ws1 and ws2:
            overlap = len(ws1 & ws2) / min(len(ws1), len(ws2))
            if overlap >= 0.7:
                return True
    return False


async def expand_topics(seeds: list[dict], rounds: int, concurrency: int) -> list[dict]:
    """
    从种子出发，利用 generate_followup 树状发散 N 轮。
    每轮对每个种子生成 derivative + extension + prerequisite 三个方向的新种子。
    """
    all_topics: dict[str, dict] = {}
    for s in seeds:
        key = s["concept"]
        all_topics[key] = {"name": s["concept"], "domain": s["domain"], "difficulty": 3, "keywords": s["keywords"]}

    current_pool = list(seeds)
    sem = asyncio.Semaphore(concurrency)

    for rnd in range(rounds):
        print(f"\n═══ Round {rnd+1}/{rounds} ═══")
        print(f"  Pool size: {len(current_pool)}")
        new_pool = []

        async def expand_one(seed: dict):
            name = seed["concept"]
            domain = seed["domain"]
            keywords = seed.get("keywords", [])

            results = []
            for route in ["derivative", "extension", "prerequisite"]:
                async with sem:
                    try:
                        fu = await generate_followup(
                            route=route,
                            current_topic_name=name,
                            current_domain=domain,
                            current_difficulty=3,
                            extracted_context={},
                            persona_level=3,
                        )
                        kw_list = fu.get("topic_keywords", [])
                        if kw_list:
                            new_name = kw_list[0]
                            if len(kw_list) > 1:
                                new_name = kw_list[0] + "与" + kw_list[1]
                            if len(new_name) > 50:
                                new_name = new_name[:50]
                            # 防呆：名称级去重
                            if new_name not in all_topics and not _is_too_similar(new_name, all_topics):
                                new_domain = domain
                                new_diff = fu.get("difficulty", 3)
                                all_topics[new_name] = {
                                    "name": new_name, "domain": new_domain,
                                    "difficulty": new_diff, "keywords": kw_list,
                                }
                                new_pool.append({"concept": new_name, "domain": new_domain, "keywords": kw_list})
                            results.append(f"{route[:4]}:{new_name[:30]}")
                    except Exception as e:
                        results.append(f"{route[:4]}:ERR")
            print(f"  {name[:40]:40s} → {', '.join(results)}")

        tasks = [expand_one(s) for s in current_pool]
        await asyncio.gather(*tasks)
        current_pool = new_pool
        print(f"  New topics this round: {len(new_pool)}")
        print(f"  Total unique topics: {len(all_topics)}")

    return list(all_topics.values())


# ═══════════════════════════════════════════
# Step 2: 生成完整内容
# ═══════════════════════════════════════════

async def _content_dedup_check(generated_data: dict) -> bool:
    """生成后内容去重：用 one_liner 编码后查 Milvus，相似度 ≥ 0.75 视为重复"""
    try:
        from src.tools.embedding import EmbeddingEncoder
        from src.tools.milvus_client import MilvusClient
        one_liner = generated_data.get("topic", {}).get("one_liner", "")
        if not one_liner:
            return False
        encoder = EmbeddingEncoder.get_instance()
        milvus = MilvusClient.get_instance()
        vec = encoder.encode(one_liner)
        hits = milvus.search_dense(vec.tolist(), top_k=1)
        if hits and hits[0].get("score", 0) >= 0.75:
            return True
    except Exception:
        pass
    return False


async def generate_all(topics: list[dict], concurrency: int):
    sem = asyncio.Semaphore(concurrency)
    stats = {"generated": 0, "skipped": 0, "failed": 0}
    completed = load_set(CHECKPOINT_GEN)

    remaining = [t for t in topics if t["name"] not in completed]
    print(f"\n═══ 生成阶段 ═══")
    print(f"  Total topics: {len(topics)}, Remaining: {len(remaining)}")

    async def process_one(t: dict):
        name = t["name"]
        domain = t["domain"]
        keywords = t.get("keywords", [])
        diff = t.get("difficulty", 3)

        async with sem:
            # L1+L2: 名称去重（阈值已收敛到 0.75）
            dup = await check_duplicate(name, domain)
            if dup.get("duplicate"):
                stats["skipped"] += 1
                return name, "skip"

            try:
                data = await generate_topic(name, domain, keywords)
            except Exception as e:
                stats["failed"] += 1
                return name, f"fail:{e}"

            # L6: 内容去重 — 生成后用 one_liner 查 Milvus 语义相似度
            if await _content_dedup_check(data):
                stats["skipped"] += 1
                return name, "skip_content"

            try:
                slave = SlaveSession(grants=[
                    CapabilityRegistry.get("save_to_postgres"),
                    CapabilityRegistry.get("save_to_milvus"),
                ])
                state = {
                    "generated_topic": data,
                    "normalized": {"core_concept": name, "domain": domain, "keywords": keywords},
                }
                await slave.execute(state)
                stats["generated"] += 1
                return name, "ok"
            except Exception as e:
                stats["failed"] += 1
                return name, f"fail:{e}"

    batch_size = 20
    for i in range(0, len(remaining), batch_size):
        batch = remaining[i:i+batch_size]
        results = await asyncio.gather(*[process_one(t) for t in batch], return_exceptions=True)

        for r in results:
            if isinstance(r, tuple):
                n, s = r
                if s == "ok":
                    completed.add(n)
                    print(f"  OK: {n[:60]}")
                elif s == "skip":
                    completed.add(n)
                    print(f"  SKIP: {n[:60]}")
                else:
                    print(f"  FAIL: {n[:60]} — {s}")

        save_set(CHECKPOINT_GEN, completed)

        g, s, f = stats["generated"], stats["skipped"], stats["failed"]
        print(f"  [{g}/{len(remaining)} gen | {s} skip | {f} fail] — sleep 3s")
        await asyncio.sleep(3)

    from src.models import Topic
    final = await Topic.all().count()
    print(f"\n  COMPLETE: DB has {final} topics")


# ═══════════════════════════════════════════
# Main
# ═══════════════════════════════════════════

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Expand topics via followup tree + generate full content")
    parser.add_argument("--rounds", type=int, default=3, help="发散轮数")
    parser.add_argument("--concurrency", type=int, default=3, help="并发数")
    parser.add_argument("--skip-expand", action="store_true", help="跳过发散阶段，直接生成")
    args = parser.parse_args()

    await init_db()
    register_all()

    if not args.skip_expand:
        print(f"\n═══ 发散阶段：{args.rounds} 轮 ═══")
        topics = await expand_topics(CORE_SEEDS, args.rounds, args.concurrency)
        save_set(CHECKPOINT_EXPAND, {t["name"] for t in topics})
    else:
        existing = load_set(CHECKPOINT_EXPAND)
        if existing:
            topics = [{"name": n, "domain": "unknown", "difficulty": 3, "keywords": []} for n in existing]
            print(f"  Loaded {len(topics)} topics from expand checkpoint")
        else:
            topics = [{"name": t["concept"], "domain": t["domain"], "difficulty": 3, "keywords": t["keywords"]} for t in CORE_SEEDS]
            print(f"  No expand checkpoint, using {len(topics)} core seeds")

    print(f"  Final topic count: {len(topics)}")

    await generate_all(topics, args.concurrency)
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
