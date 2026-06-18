"""
全链路端到端测试：生成 10 道题 → 写入 PG + Milvus → 验证
"""
import asyncio
import json
import time
from src.config.settings import settings
from dataclasses import dataclass, field
from typing import Any
from tortoise.transactions import in_transaction

# ── 10 道测试题目 ──

TEST_TOPICS = [
    # 后端开发 (4)
    {"core_concept": "HashMap底层实现",       "domain": "编程基础", "keywords": ["HashMap", "哈希表", "红黑树", "哈希冲突", "链表"]},
    {"core_concept": "ConcurrentHashMap原理", "domain": "编程基础", "keywords": ["ConcurrentHashMap", "CAS", "synchronized", "分段锁"]},
    {"core_concept": "JVM内存模型",           "domain": "编程基础", "keywords": ["JVM", "堆", "栈", "方法区", "GC"]},
    {"core_concept": "Java线程池",            "domain": "编程基础", "keywords": ["ThreadPoolExecutor", "核心线程", "阻塞队列", "拒绝策略"]},
    # 数据库 (3)
    {"core_concept": "MySQL索引原理",         "domain": "数据库",   "keywords": ["B+树", "聚簇索引", "覆盖索引", "索引下推", "Explain"]},
    {"core_concept": "事务隔离级别",           "domain": "数据库",   "keywords": ["MVCC", "脏读", "不可重复读", "幻读", "锁"]},
    {"core_concept": "数据库连接池",           "domain": "数据库",   "keywords": ["连接池", "HikariCP", "Druid", "连接复用"]},
    # 消息队列 (3)
    {"core_concept": "Kafka消息可靠性",        "domain": "系统设计", "keywords": ["Kafka", "ISR", "ACK", "幂等", "ExactlyOnce"]},
    {"core_concept": "RabbitMQ工作模式",       "domain": "系统设计", "keywords": ["RabbitMQ", "Exchange", "Queue", "路由", "TTL"]},
    {"core_concept": "消息队列幂等性",         "domain": "系统设计", "keywords": ["幂等", "去重", "消息队列", "唯一ID", "Redis"]},
]


@dataclass
class TopicReport:
    index: int
    name: str
    domain: str
    time_s: float = 0.0
    topic_id: str = ""
    # Content
    content_score: int = 0
    content_details: list[str] = field(default_factory=list)
    # Topology
    topology: dict = field(default_factory=dict)
    # Recall
    recall_hits: dict = field(default_factory=dict)
    # Errors
    errors: list[str] = field(default_factory=list)


def _pass_fail(check: bool, label: str) -> str:
    return "✅" if check else "❌"


def validate_content(data: dict) -> tuple[int, list[str]]:
    """求职者维度检查，返回 (得分, 详情列表)"""
    t = data.get("topic", {})
    details = []
    score = 0
    total = 10

    # A1: one_liner 40-80字
    ol = t.get("one_liner", "")
    ok = ol and 40 <= len(ol) <= 80
    details.append(f"{_pass_fail(ok,'A1')} one_liner: {len(ol)}字")
    score += int(ok)

    # A2: core_summary 30-60字
    cs = t.get("core_summary", "")
    ok = cs and 30 <= len(cs) <= 60
    details.append(f"{_pass_fail(ok,'A2')} core_summary: {len(cs)}字")
    score += int(ok)

    # A3: detailed_explanation 200-500字
    de = t.get("detailed_explanation", "")
    ok = de and 200 <= len(de) <= 500
    details.append(f"{_pass_fail(ok,'A3')} detailed_explanation: {len(de)}字")
    score += int(ok)

    # A4: core_points 2-4条
    cp = t.get("core_points", "")
    pts = [p for p in str(cp).split("\n") if p.strip()] if isinstance(cp, str) else (cp if isinstance(cp, list) else [])
    ok = 2 <= len(pts) <= 5
    details.append(f"{_pass_fail(ok,'A4')} core_points: {len(pts)}条")
    score += int(ok)

    # A5: code_example
    ce = t.get("code_example", "")
    ok = bool(ce and len(ce) > 10)
    details.append(f"{_pass_fail(ok,'A5')} code_example: {'有' if ok else '无'}")
    score += int(ok)

    # A6: traps
    tr = t.get("traps", "")
    ok = bool(tr and len(tr) > 20)
    details.append(f"{_pass_fail(ok,'A6')} traps: {len(str(tr))}字")
    score += int(ok)

    # A7: bonuses
    bo = t.get("bonuses", "")
    ok = bool(bo and len(str(bo)) > 20)
    details.append(f"{_pass_fail(ok,'A7')} bonuses: {len(str(bo))}字")
    score += int(ok)

    # A8: keywords
    kw = t.get("keywords", [])
    if isinstance(kw, str):
        kw = [kw]
    has_cn = any(ord(c) > 127 for item in kw for c in str(item))
    has_en = any(ord(c) < 128 for item in kw for c in str(item) if c.isalpha())
    ok = 3 <= len(kw) <= 5 and has_cn and has_en
    details.append(f"{_pass_fail(ok,'A8')} keywords: {len(kw)}个, 含中文={has_cn}, 含英文={has_en}")
    score += int(ok)

    # A9: evaluation_anchors
    ea = data.get("evaluation_anchors", [])
    levels = {e.get("level") for e in ea}
    has_q = all(e.get("question") for e in ea)
    has_a = all(e.get("expected_answer") for e in ea)
    ok = len(ea) >= 2 and "entry" in levels and has_q and has_a
    details.append(f"{_pass_fail(ok,'A9')} eval_anchors: {len(ea)}级 ({sorted(levels)})")
    score += int(ok)

    # A10: tech_domain
    td = t.get("tech_domain", "")
    ok = bool(td)
    details.append(f"{_pass_fail(ok,'A10')} tech_domain={td}")
    score += int(ok)

    return score, details


def validate_topology(data: dict) -> dict:
    """拓扑关系检查"""
    kps = data.get("knowledge_points", [])
    by_type = {}
    for kp in kps:
        by_type.setdefault(kp["type"], []).append(kp)

    total = {"prerequisite": len(by_type.get("prerequisite", [])),
             "core_concept": len(by_type.get("core_concept", [])),
             "derivative": len(by_type.get("derivative", [])),
             "extension": len(by_type.get("extension", []))}

    issues = []
    # 检查重要性分布
    for kp in kps:
        if kp["type"] in ("prerequisite", "core_concept") and kp.get("importance", 0) < 4:
            issues.append(f"{kp['type']} '{kp['name']}' importance={kp['importance']} 偏低，建议>=4")

    for kp in kps:
        if kp["type"] == "derivative" and not kp.get("description", ""):
            issues.append(f"derivative '{kp['name']}' 缺少 description")
        # 检查 name 独立性
        name = kp["name"]
        if len(name) < 2 or name.endswith("机制") or name.endswith("函数"):
            issues.append(f"'{name}' 可能不够独立作为题目标题")

    return {"counts": total, "total": len(kps), "issues": issues, "by_type": by_type}


async def run_full_pipeline():
    """主流程"""
    from src.config.database import db_lifespan

    async with db_lifespan():
        # ── 0. 清空数据 ──
        from src.models.topic import Topic
        from src.models.knowledge_dict import KnowledgeDict
        from src.models.topic_prerequisite import TopicPrerequisite
        from src.models.topic_core_concept import TopicCoreConcept
        from src.models.topic_derivative import TopicDerivative
        from src.models.topic_extension import TopicExtension
        from src.models.topic_evaluation_anchor import TopicEvaluationAnchor
        from src.models.topic_similar_question import TopicSimilarQuestion
        from src.models.topic_advanced_question import TopicAdvancedQuestion
        from src.models.topic_reference import TopicReference

        async with in_transaction():
            await TopicPrerequisite.all().delete()
            await TopicCoreConcept.all().delete()
            await TopicDerivative.all().delete()
            await TopicExtension.all().delete()
            await TopicEvaluationAnchor.all().delete()
            await TopicSimilarQuestion.all().delete()
            await TopicAdvancedQuestion.all().delete()
            await TopicReference.all().delete()
            await KnowledgeDict.all().delete()
            await Topic.all().delete()
        print(f"🗑️  DB cleaned. Topics remaining: {await Topic.all().count()}")

        # 清理 Milvus 旧数据
        from src.tools.milvus_client import MilvusClient
        mc = MilvusClient.get_instance()
        if mc.available:
            from pymilvus import Collection as MColl, utility
            if utility.has_collection("topic_embeddings"):
                utility.drop_collection("topic_embeddings")
            if utility.has_collection("knowledge_embeddings"):
                utility.drop_collection("knowledge_embeddings")
            print("🗑️  Milvus collections cleaned")
        mc.init_collection()
        mc.init_knowledge_embeddings_collection()
        print("📦 Milvus collections ready (index will be built after inserts)")

        from src.agentv3.capabilities.generate import generate_topic
        from src.agentv3.capabilities.write import save_to_postgres, save_to_milvus

        reports: list[TopicReport] = []

        for i, spec in enumerate(TEST_TOPICS):
            name = spec["core_concept"]
            print(f"\n{'='*60}")
            print(f"  [{i+1}/10] {name} ({spec['domain']})")
            print(f"{'='*60}")

            r = TopicReport(index=i+1, name=name, domain=spec["domain"])

            try:
                t0 = time.time()

                # Step 1: Generate
                data = await generate_topic(name, spec["domain"], spec["keywords"])
                r.time_s = round(time.time() - t0, 1)
                print(f"  ⏱️  Generated in {r.time_s}s")

                # Step 2: Content validation
                score, details = validate_content(data)
                r.content_score = score
                r.content_details = details
                print(f"  📝 Content: {score}/10")
                for d in details:
                    print(f"     {d}")

                # Step 3: Topology validation
                topo = validate_topology(data)
                r.topology = topo
                print(f"  🔗 Topology: {topo['total']} knowledge_points ({topo['counts']})")
                if topo["issues"]:
                    for issue in topo["issues"]:
                        print(f"     ⚠️  {issue}")

                # Step 4: Save to PG
                wr = await save_to_postgres(data)
                r.topic_id = wr.get("topic_id", "")
                print(f"  💾 PG: {'created' if wr.get('created') else 'SKIPPED (exists)'}  id={r.topic_id[:8]}")

                # Step 5: Save to Milvus
                kps = data.get("knowledge_points", [])
                core_pts = next((kp for kp in kps if kp["type"] == "core_concept"), None)
                concept_to_encode = core_pts["name"] if core_pts else name
                mr = await save_to_milvus(
                    r.topic_id, concept_to_encode, spec["domain"],
                    ",".join(spec["keywords"]),
                    data.get("topic", {}).get("difficulty", 3)
                )
                print(f"  📦 Milvus: {'✅' if mr.get('success') else '❌ ' + mr.get('error', 'unknown')}")

            except Exception as e:
                r.errors.append(str(e))
                print(f"  ❌ ERROR: {e}")

            reports.append(r)

        # ── Step 6: 构建 Milvus 索引 ──
        print(f"\n{'='*60}")
        print(f"  构建 HNSW 索引")
        print(f"{'='*60}")
        mc.build_index()
        mc.build_knowledge_index()
        print(f"  HNSW indexes built. topics={mc.count()} knowledge={mc.count_knowledge_embeddings()}")

        # ── Step 7: 验证 PG 数据 ──
        print(f"\n{'='*60}")
        print(f"  数据库验证")
        print(f"{'='*60}")
        print(f"  topic:              {await Topic.all().count()}")
        print(f"  knowledge_dict:     {await KnowledgeDict.all().count()}")
        print(f"  prerequisite:       {await TopicPrerequisite.all().count()}")
        print(f"  core_concept:       {await TopicCoreConcept.all().count()}")
        print(f"  derivative:         {await TopicDerivative.all().count()}")
        print(f"  extension:          {await TopicExtension.all().count()}")
        print(f"  eval_anchor:        {await TopicEvaluationAnchor.all().count()}")

        # ── Step 8: 召回测试 ──
        print(f"\n{'='*60}")
        print(f"  召回测试")
        print(f"{'='*60}")

        from src.agentv3.capabilities.search import search_knowledge

        # Collect topic_ids for recall verification
        topic_ids = {r.name: r.topic_id for r in reports if r.topic_id}

        recall_tests = [
            ("精确召回", "HashMap底层实现", True),
            ("相关召回", "线程安全 Map", True),
            ("拓扑召回", "哈希冲突", True),
            ("噪声排除", "前端框架 React Hooks", False),
        ]

        for test_name, query, expect_hit in recall_tests:
            hits = await search_knowledge(query, query.split(), top_k=5)
            candidates = hits.get("candidates", [])
            hit_count = len(candidates)
            # 通过 topic_id 匹配
            matched_ids = {
                h.get("topic_id") for h in candidates if h.get("topic_id")
            }
            known_ids = set(topic_ids.values())
            found = bool(matched_ids & known_ids)
            status = "✅" if found == expect_hit else "⚠️"
            print(f"  {status} {test_name}: '{query}' → {hit_count} candidates, expected_hit={expect_hit}, actual_hit={found}")
            if candidates:
                top = candidates[0]
                print(f"      top: concept={top.get('core_concept', 'N/A')[:30]}  rrf={top.get('rrf_score', 0):.4f}")

        # ── Step 9: 汇总报告 ──
        print(f"\n{'='*60}")
        print(f"  汇总报告")
        print(f"{'='*60}")

        by_domain = {}
        for rp in reports:
            by_domain.setdefault(rp.domain, []).append(rp)

        for domain, rps in by_domain.items():
            avg_content = sum(r.content_score for r in rps) / max(len(rps), 1)
            total_kp = sum(r.topology.get("total", 0) for r in rps if r.topology)
            coverage = all(
                r.topology.get("counts", {}).get(t, 0) > 0
                for t in ("prerequisite", "core_concept", "derivative", "extension")
                for r in rps
            )
            print(f"\n  [{domain}]")
            print(f"    题目数: {len(rps)}")
            print(f"    内容平均分: {avg_content:.1f}/10")
            print(f"    知识点总数: {total_kp}")
            print(f"    四类型全覆盖: {'是' if coverage else '否'}")

            for rp in rps:
                errs = f" (ERRORS: {len(rp.errors)})" if rp.errors else ""
                topo_total = rp.topology.get("total", 0) if rp.topology else 0
                print(f"      {rp.name}: content={rp.content_score}/10  topo={topo_total}kp  milvus={'✅' if rp.topic_id else '❌'}{errs}")

        avg = sum(r.content_score for r in reports) / len(reports)
        total_kp = sum(r.topology.get("total", 0) for r in reports)
        errors = [r for r in reports if r.errors]
        print(f"\n  🏆 总计: {len(reports)}题, 内容均分={avg:.1f}/10, 知识点总计={total_kp}, 错误题数={len(errors)}")
        return reports


if __name__ == "__main__":
    asyncio.run(run_full_pipeline())
