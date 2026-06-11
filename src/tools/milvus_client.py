"""
Milvus 向量数据库客户端 (可选)
如果 Milvus 不可达，所有操作优雅降级
"""
from typing import Optional
from src.config.settings import settings

COLLECTION_NAME = "topic_embeddings"
DIM = 1024


class MilvusClient:
    _instance: Optional["MilvusClient"] = None

    def __init__(self):
        self.host = settings.MILVUS_HOST
        self.port = settings.MILVUS_PORT
        self._available: Optional[bool] = None  # None = 未探测

    @classmethod
    def get_instance(cls) -> "MilvusClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _check_available(self) -> bool:
        """延迟探测 Milvus 是否可用"""
        if self._available is not None:
            return self._available
        try:
            from pymilvus import connections, utility
            connections.connect(alias="__check", host=self.host, port=self.port, timeout=3)
            self._available = True
            connections.disconnect("__check")
        except Exception:
            self._available = False
        return self._available

    @property
    def available(self) -> bool:
        return self._check_available()

    def search_dense(self, query_vector: list[float], top_k: int = 10) -> list[dict]:
        if not self._check_available():
            return []
        try:
            from pymilvus import Collection
            collection = Collection(COLLECTION_NAME)
            collection.load()
            results = collection.search(
                data=[query_vector],
                anns_field="embedding",
                param={"metric_type": "COSINE", "params": {"ef": 128}},
                limit=top_k,
                output_fields=["topic_id", "core_concept", "domain", "keywords", "difficulty"],
            )
            hits = []
            for hits_list in results:
                for hit in hits_list:
                    hits.append({
                        "id": hit.id,
                        "topic_id": hit.entity.get("topic_id"),
                        "core_concept": hit.entity.get("core_concept"),
                        "domain": hit.entity.get("domain"),
                        "keywords": hit.entity.get("keywords"),
                        "difficulty": hit.entity.get("difficulty"),
                        "score": hit.distance,
                    })
            return hits
        except Exception:
            return []

    def search_sparse(self, keywords: list[str], top_k: int = 10) -> list[dict]:
        if not self._check_available():
            return []
        try:
            from pymilvus import Collection
            collection = Collection(COLLECTION_NAME)
            collection.load()
            expr_parts = [f'keywords like "%{kw}%"' for kw in keywords if kw]
            if not expr_parts:
                return []
            expr = " or ".join(expr_parts)
            return collection.query(expr=expr, limit=top_k,
                                     output_fields=["topic_id", "core_concept", "domain", "keywords", "difficulty"])
        except Exception:
            return []

    def insert(self, topic_id, core_concept, embedding, domain, keywords, difficulty=3):
        if not self._check_available():
            return
        try:
            from pymilvus import Collection
            collection = Collection(COLLECTION_NAME)
            collection.load()
            collection.insert([[topic_id], [core_concept], [embedding], [domain], [keywords], [difficulty]])
            collection.flush()
        except Exception:
            pass

    def init_collection(self):
        """仅在 Milvus 可用时初始化"""
        if not self._check_available():
            return
        try:
            from pymilvus import Collection, FieldSchema, CollectionSchema, DataType, utility
            if utility.has_collection(COLLECTION_NAME):
                return
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="topic_id", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="core_concept", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=DIM),
                FieldSchema(name="domain", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="keywords", dtype=DataType.VARCHAR, max_length=512),
                FieldSchema(name="difficulty", dtype=DataType.INT64),
            ]
            schema = CollectionSchema(fields, description="Topic Embedding Collection")
            collection = Collection(COLLECTION_NAME, schema)
            index_params = {"metric_type": "COSINE", "index_type": "HNSW", "params": {"M": 16, "efConstruction": 200}}
            collection.create_index(field_name="embedding", index_params=index_params)
            collection.load()
        except Exception:
            pass

    def count(self) -> int:
        if not self._check_available():
            return 0
        try:
            from pymilvus import Collection
            return Collection(COLLECTION_NAME).num_entities
        except Exception:
            return 0
