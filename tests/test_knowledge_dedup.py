"""知识点去重单元测 —— 只测 Milvus 索引 + dedup 链路，不调 LLM 生成"""
import asyncio
import traceback
from src.models.knowledge_dict import KnowledgeDict
from src.models.knowledge_alias import KnowledgeAlias
from src.tools.milvus_client import MilvusClient
from src.agentv3.capabilities.write import _upsert_knowledge


async def test_index_flow():
    """测试：建 collection → 插入 → 建索引 → 搜索 → dedup"""
    from src.config.database import db_lifespan

    async with db_lifespan():
        # 清空
        await KnowledgeAlias.all().delete()
        await KnowledgeDict.all().delete()
        mc = MilvusClient.get_instance()
        assert mc.available, "Milvus must be available"
        from pymilvus import utility
        for c in ["knowledge_embeddings"]:
            if utility.has_collection(c):
                utility.drop_collection(c)

        mc.init_knowledge_embeddings_collection()
        print("1. Collection created")

        # Step 1: 插入第一个知识点
        kd1 = await _upsert_knowledge("多版本并发控制", "MVCC的完整描述")
        print(f"2. Inserted: {kd1.name}  embeddings_count={mc.count_knowledge_embeddings()}")

        # Step 2: 建索引 —— 关键步骤
        mc.build_knowledge_index()
        print(f"3. Index built. count={mc.count_knowledge_embeddings()}")

        # Step 3: 搜索验证
        from src.tools.embedding import EmbeddingEncoder
        e = EmbeddingEncoder.get_instance()
        v = e.encode("MVCC 多版本并发控制")
        hits = mc.search_knowledge_embeddings(v.tolist(), top_k=3)
        print(f"4. Search hits: {len(hits)}")
        for h in hits:
            print(f"   name={h.get('name'):20s} score={h.get('score'):.4f}")

        assert len(hits) > 0, "搜索应返回至少 1 条结果"
        assert hits[0]["name"] == "多版本并发控制", f"应命中多版本并发控制，实际: {hits[0]['name']}"
        print("5. ✅ Search works after index build")

        # Step 4: 去重 —— "MVCC" 应被映射到 "多版本并发控制"
        # 先 flush 确保上一步的数据落盘
        mc.flush_knowledge_embeddings()
        mc.build_knowledge_index()
        
        kd2 = await _upsert_knowledge("MVCC", "多版本并发控制的缩写")
        assert kd2.id == kd1.id, f"MVCC 应去重到多版本并发控制，kd1={kd1.id} kd2={kd2.id}"
        print(f"6. ✅ Dedup works: MVCC → {kd2.name}")

        # Step 5: alias 写入验证
        alias = await KnowledgeAlias.filter(knowledge_id=kd1.id).first()
        assert alias is not None, "应写入 alias 记录"
        print(f"7. ✅ Alias written: {alias.alias} → {kd1.name}")

        # 最终状态
        total = await KnowledgeDict.all().count()
        assert total == 1, f"knowledge_dict 应为 1 条，实际 {total}"
        print(f"8. ✅ knowledge_dict total={total}")

    print("\n🏆 All tests passed")


async def test_index_rebuild():
    """测试：先有数据，后建索引，搜索应可用"""
    from src.config.database import db_lifespan

    async with db_lifespan():
        await KnowledgeAlias.all().delete()
        await KnowledgeDict.all().delete()
        mc = MilvusClient.get_instance()
        assert mc.available, "Milvus must be available"
        from pymilvus import utility
        for c in ["knowledge_embeddings"]:
            if utility.has_collection(c):
                utility.drop_collection(c)
        mc.init_knowledge_embeddings_collection()

        # 先插入多条数据
        from src.agentv3.capabilities.write import _sync_knowledge_embedding
        kd_a = await KnowledgeDict.create(name="哈希冲突", description="核心概念")
        kd_b = await KnowledgeDict.create(name="红黑树", description="数据结构")
        kd_c = await KnowledgeDict.create(name="链表", description="数据结构")
        await _sync_knowledge_embedding(kd_a)
        await _sync_knowledge_embedding(kd_b)
        await _sync_knowledge_embedding(kd_c)
        print(f"1. Inserted 3 KDs. embeddings={mc.count_knowledge_embeddings()}")

        # 现在建索引
        mc.build_knowledge_index()
        print(f"2. Index built")

        # 搜索
        from src.tools.embedding import EmbeddingEncoder
        e = EmbeddingEncoder.get_instance()
        for query, expected in [("哈希冲突", "哈希冲突"), ("红黑树", "红黑树"), ("HashMap", None)]:
            v = e.encode(query)
            hits = mc.search_knowledge_embeddings(v.tolist(), top_k=3)
            if expected:
                assert len(hits) > 0, f"查询 '{query}' 应返回结果"
                found = any(expected in h.get("name", "") for h in hits)
                assert found, f"查询 '{query}' 应命中 '{expected}'，实际: {[h.get('name') for h in hits]}"
                print(f"3. ✅ '{query}' → {hits[0].get('name')} (score={hits[0].get('score'):.4f})")
            else:
                print(f"3. ℹ️  '{query}' → {len(hits)} hits (预期非精确匹配)")

    print("\n🏆 All tests passed")


if __name__ == "__main__":
    asyncio.run(test_index_flow())
    print("\n" + "=" * 60)
    asyncio.run(test_index_rebuild())
