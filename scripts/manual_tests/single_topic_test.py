"""单题全链路测试 —— 带时间日志"""
import asyncio
import time
from src.config.settings import settings


async def main():
    from src.config.database import db_lifespan

    t_total = time.time()

    async with db_lifespan():
        # 清空
        from src.models.knowledge_dict import KnowledgeDict
    from src.models.knowledge_alias import KnowledgeAlias
    from src.models.topic import Topic
    from src.models.topic_prerequisite import TopicPrerequisite
    from src.models.topic_core_concept import TopicCoreConcept
    from src.models.topic_derivative import TopicDerivative
    from src.models.topic_extension import TopicExtension
    from src.models.topic_evaluation_anchor import TopicEvaluationAnchor

    async with in_transaction():
        await TopicPrerequisite.all().delete()
        await TopicCoreConcept.all().delete()
        await TopicDerivative.all().delete()
        await TopicExtension.all().delete()
        await TopicEvaluationAnchor.all().delete()
        await KnowledgeAlias.all().delete()
        await KnowledgeDict.all().delete()
        await Topic.all().delete()
    print(f"0b. DB cleaned")

    # 清空 Milvus
    from src.tools.milvus_client import MilvusClient
    mc = MilvusClient.get_instance()
    topic_count = mc.count()
    kd_milvus = mc.count_knowledge_embeddings()
    assert mc.available
    from pymilvus import utility
    for c in ["topic_embeddings", "knowledge_embeddings"]:
        if utility.has_collection(c):
            utility.drop_collection(c)
    mc.init_collection()
    mc.init_knowledge_embeddings_collection()

    # ── 1. 生成 ──
    t1 = time.time()
    from src.agentv3.capabilities.generate import generate_topic
    data = await generate_topic("HashMap底层实现", "编程基础", ["HashMap", "哈希表", "红黑树"])
    print(f"1. LLM generate: {time.time()-t1:.1f}s")

    # ── 2. 写 PG ──
    t2 = time.time()
    from src.agentv3.capabilities.write import save_to_postgres
    wr = await save_to_postgres(data)
    print(f"2. PG write: {time.time()-t2:.1f}s  created={wr.get('created')}")

    # ── 2b. 逐知识点耗时 ──
    print("    per-KP:")
    from src.agentv3.capabilities.write import _upsert_knowledge
    for kp in data.get("knowledge_points", []):
        tk = time.time()
        await _upsert_knowledge(kp["name"], kp.get("description"))
        print(f"      {kp['type']:15s} {kp['name']:25s} {time.time()-tk:.2f}s")

    # ── 3. 建索引 ──
    t3 = time.time()
    mc.build_index()
    mc.build_knowledge_index()
    print(f"3. Build indexes: {time.time()-t3:.1f}s")

    # ── 4. 写 Milvus ──
    t4 = time.time()
    from src.agentv3.capabilities.write import save_to_milvus
    kps = data.get("knowledge_points", [])
    core = next((kp for kp in kps if kp["type"] == "core_concept"), None)
    concept = core["name"] if core else "HashMap底层实现"
    mr = await save_to_milvus(wr["topic_id"], concept, "编程基础", "HashMap,哈希表,红黑树", data.get("topic", {}).get("difficulty", 3))
    print(f"4. Milvus write: {time.time()-t4:.1f}s  ok={mr.get('success')}")

    # ── 5. 召回 ──
    t5 = time.time()
    from src.agentv3.capabilities.search import search_knowledge
    hits = await search_knowledge("HashMap底层实现", ["HashMap", "哈希表"], top_k=5)
    print(f"5. Recall search: {time.time()-t5:.1f}s  candidates={len(hits.get('candidates',[]))}")
    for h in hits.get("candidates", [])[:3]:
        print(f"   {h.get('core_concept',''):25s} rrf={h.get('rrf_score',0):.4f}")

    # ── 检查数据库 ──
    kd_count = await KnowledgeDict.all().count()
    topic_pg = await Topic.all().count()
    print(f"6. knowledge_dict={kd_count}  topic_pg={topic_pg}  milvus_topic={mc.count()}")

    print(f"\nTotal: {time.time()-t_total:.1f}s")

asyncio.run(main())
