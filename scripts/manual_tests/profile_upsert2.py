"""极致耗时分析 —— 人工拆分 _upsert_knowledge 的三层"""
import asyncio, time
from src.config.settings import settings


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

    from src.agentv3.capabilities.write import KnowledgeDict as KDC

    for i, name in enumerate(["哈希表", "哈希冲突", "红黑树", "链表"]):
        print(f"\n--- KP {i+1}: {name} ---")
        t0 = time.time()

        # Layer 0
        t = time.time()
        existing = await KnowledgeDict.filter(name=name).first()
        print(f"  L0 filter: {time.time()-t:.3f}s")

        # Layer 1
        t = time.time()
        alias = await KnowledgeAlias.filter(alias=name).first()
        if alias:
            await alias.fetch_related("knowledge")
        print(f"  L1 alias: {time.time()-t:.3f}s  hit={alias is not None}")

        # Layer 2 — BGE
        from src.tools.embedding import EmbeddingEncoder
        t = time.time()
        e = EmbeddingEncoder.get_instance()
        v = e.encode(name)
        print(f"  L2a BGE: {time.time()-t:.3f}s  dim={len(v)}")

        # Layer 2 — build index
        t = time.time()
        mc.build_knowledge_index()
        print(f"  L2b build_idx: {time.time()-t:.3f}s")

        # Layer 2 — search
        t = time.time()
        hits = mc.search_knowledge_embeddings(v.tolist(), top_k=3)
        print(f"  L2c search: {time.time()-t:.3f}s  hits={len(hits)}")
        for h in hits:
            print(f"       {h.get('name')}:{h.get('score'):.3f}")

        # create KD
        await KnowledgeDict.create(name=name, description="test")
        # sync embedding
        from src.agentv3.capabilities.write import _sync_knowledge_embedding
        t = time.time()
        kd = await KnowledgeDict.filter(name=name).first()
        await _sync_knowledge_embedding(kd)
        print(f"  L2d sync_emb: {time.time()-t:.3f}s")

        print(f"  TOTAL: {time.time()-t0:.2f}s")

asyncio.run(main())
