"""知识点去重测试 —— 测 Milvus 索引 + dedup 链路,不调 LLM 生成

⚠️ 标记 e2e + slow:依赖真实 Milvus,默认跳过
"""
import pytest

from src.agentv3.capabilities.write import _upsert_knowledge
from src.models.knowledge_alias import KnowledgeAlias
from src.models.knowledge_dict import KnowledgeDict
from src.tools.milvus_client import MilvusClient

pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.asyncio]


async def test_index_flow(db):
    """测试:建 collection → 插入 → 建索引 → 搜索 → dedup"""
    await KnowledgeAlias.all().delete()
    await KnowledgeDict.all().delete()
    mc = MilvusClient.get_instance()
    if not mc.available:
        pytest.skip("Milvus not available — skip e2e dedup test")
    from pymilvus import utility
    for c in ["knowledge_embeddings"]:
        if utility.has_collection(c):
            utility.drop_collection(c)

    mc.init_knowledge_embeddings_collection()

    # Step 1: 插入第一个知识点
    kd1 = await _upsert_knowledge("多版本并发控制", "MVCC的完整描述")

    # Step 2: 建索引
    mc.build_knowledge_index()

    # Step 3: 搜索验证
    from src.tools.embedding import EmbeddingEncoder
    e = EmbeddingEncoder.get_instance()
    v = e.encode("MVCC 多版本并发控制")
    hits = mc.search_knowledge_embeddings(v.tolist(), top_k=3)

    assert len(hits) > 0, "搜索应返回至少 1 条结果"
    assert hits[0]["name"] == "多版本并发控制", f"应命中多版本并发控制,实际: {hits[0]['name']}"

    # Step 4: dedup —— "MVCC" 应被映射到 "多版本并发控制"
    mc.flush_knowledge_embeddings()
    mc.build_knowledge_index()

    kd2 = await _upsert_knowledge("MVCC", "多版本并发控制的缩写")
    assert kd2.id == kd1.id, f"MVCC 应去重到多版本并发控制,kd1={kd1.id} kd2={kd2.id}"

    # Step 5: alias 写入验证
    alias = await KnowledgeAlias.filter(knowledge_id=kd1.id).first()
    assert alias is not None, "应写入 alias 记录"

    # 最终状态
    total = await KnowledgeDict.all().count()
    assert total == 1, f"knowledge_dict 应为 1 条,实际 {total}"


async def test_index_rebuild(db):
    """测试:先有数据,后建索引,搜索应可用"""
    await KnowledgeAlias.all().delete()
    await KnowledgeDict.all().delete()
    mc = MilvusClient.get_instance()
    if not mc.available:
        pytest.skip("Milvus not available — skip e2e dedup test")
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

    # 现在建索引
    mc.build_knowledge_index()

    # 搜索
    from src.tools.embedding import EmbeddingEncoder
    e = EmbeddingEncoder.get_instance()
    for query, expected in [("哈希冲突", "哈希冲突"), ("红黑树", "红黑树"), ("HashMap", None)]:
        v = e.encode(query)
        hits = mc.search_knowledge_embeddings(v.tolist(), top_k=3)
        if expected:
            assert len(hits) > 0, f"查询 '{query}' 应返回结果"
            found = any(expected in h.get("name", "") for h in hits)
            assert found, f"查询 '{query}' 应命中 '{expected}',实际: {[h.get('name') for h in hits]}"
