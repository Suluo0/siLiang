"""逐知识点 _upsert_knowledge 耗时分析"""
import asyncio, time
from src.config.settings import settings

KPS = [
    {"name": "哈希表", "type": "prerequisite", "description": "HashMap的理论基础"},
    {"name": "哈希冲突", "type": "core_concept", "description": "不同key映射到同一槽位"},
    {"name": "红黑树", "type": "core_concept", "description": "自平衡二叉查找树"},
    {"name": "链表", "type": "core_concept", "description": "线性数据结构"},
    {"name": "ConcurrentHashMap", "type": "derivative", "description": "HashMap的线程安全版本"},
    {"name": "TreeMap", "type": "derivative", "description": "基于红黑树实现的有序Map"},
    {"name": "哈希算法设计", "type": "extension", "description": "更深层的哈希原理"},
    {"name": "HashMap扩容机制详解", "type": "extension", "description": "深入分析扩容流程"},
]


async def main():
    from src.config.database import db_lifespan

    async with db_lifespan():
        from src.models.knowledge_dict import KnowledgeDict
    from src.models.knowledge_alias import KnowledgeAlias
    await KnowledgeAlias.all().delete()
    await KnowledgeDict.all().delete()
    from src.tools.milvus_client import MilvusClient
    mc = MilvusClient.get_instance()
    assert mc.available
    from pymilvus import utility
    if utility.has_collection("knowledge_embeddings"):
        utility.drop_collection("knowledge_embeddings")
    mc.init_knowledge_embeddings_collection()

    from src.agentv3.capabilities.write import _upsert_knowledge

    for kp in KPS:
        t0 = time.time()
        kd = await _upsert_knowledge(kp["name"], kp["description"])
        elapsed = time.time() - t0
        new = "NEW" if kd.description == kp["description"] else "DEDUP"
        print(f"{new:5s} {kp['type']:15s} {kp['name']:30s} {elapsed:.2f}s")

asyncio.run(main())
