"""
Milvus 向量数据库客户端 (可选)
如果 Milvus 不可达，所有操作优雅降级
"""
from typing import Optional
from src.config.settings import settings

COLLECTION_NAME = "topic_embeddings"
TABLE_SCHEMAS_COLLECTION = "table_schemas"
KNOWLEDGE_EMBEDDINGS_COLLECTION = "knowledge_embeddings"
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

    def _ensure_connection(self) -> bool:
        """确保与 Milvus 的持久连接已建立"""
        try:
            from pymilvus import connections
            # 检查已有连接
            conn = connections._fetch_handler("default")
            if conn:
                return True
        except Exception:
            pass
        try:
            from pymilvus import connections
            connections.connect(alias="default", host=self.host, port=self.port, timeout=10)
            self._available = True
            return True
        except Exception:
            self._available = False
            return False

    def _check_available(self) -> bool:
        """延迟探测 Milvus 是否可用"""
        if self._available is not None:
            return self._available
        return self._ensure_connection()

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
                                     output_fields=["id", "topic_id", "core_concept", "domain", "keywords", "difficulty"])
        except Exception:
            return []

    def insert(self, topic_id, core_concept, embedding, domain, keywords, difficulty=3):
        if not self._check_available():
            return
        from pymilvus import Collection
        self.init_collection()
        collection = Collection(COLLECTION_NAME)
        collection.insert([[topic_id], [core_concept], [embedding], [domain], [keywords], [difficulty]])
        collection.flush()

    def init_collection(self):
        """仅在 Milvus 可用时初始化（不建索引，索引在插入数据后单独调用 build_index）"""
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
        except Exception:
            pass

    def build_index(self):
        """在数据插入后构建 HNSW 索引"""
        if not self._check_available():
            return
        try:
            from pymilvus import Collection
            collection = Collection(COLLECTION_NAME)
            index_params = {"metric_type": "COSINE", "index_type": "HNSW", "params": {"M": 16, "efConstruction": 200}}
            collection.create_index(field_name="embedding", index_params=index_params)
            collection.load()
        except Exception:
            pass

    def init_table_schemas_collection(self):
        """初始化表结构文档集合"""
        if not self._check_available():
            return
        try:
            from pymilvus import Collection, FieldSchema, CollectionSchema, DataType, utility
            if utility.has_collection(TABLE_SCHEMAS_COLLECTION):
                return
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="table_name", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="description", dtype=DataType.VARCHAR, max_length=1024),
                FieldSchema(name="schema_text", dtype=DataType.VARCHAR, max_length=3000),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=DIM),
            ]
            schema = CollectionSchema(fields, description="Table Schema Documents")
            collection = Collection(TABLE_SCHEMAS_COLLECTION, schema)
            index_params = {"metric_type": "COSINE", "index_type": "HNSW", "params": {"M": 16, "efConstruction": 200}}
            collection.create_index(field_name="embedding", index_params=index_params)
            collection.load()
        except Exception:
            pass

    def upsert_table_schema(self, table_name: str, description: str, schema_text: str, embedding: list[float]):
        """写入或更新单条表结构文档"""
        if not self._check_available():
            return
        try:
            from pymilvus import Collection
            collection = Collection(TABLE_SCHEMAS_COLLECTION)
            collection.load()
            # 先删旧数据（按 table_name 精确匹配）
            collection.query(expr=f'table_name == "{table_name}"')
            collection.delete(expr=f'table_name == "{table_name}"')
            collection.insert([[table_name], [description], [schema_text], [embedding]])
            collection.flush()
        except Exception:
            pass

    def search_table_schemas(self, query_vector: list[float], top_k: int = 8) -> list[dict]:
        """按查询意图检索最相关的表结构"""
        if not self._check_available():
            return []
        try:
            from pymilvus import Collection
            collection = Collection(TABLE_SCHEMAS_COLLECTION)
            collection.load()
            results = collection.search(
                data=[query_vector],
                anns_field="embedding",
                param={"metric_type": "COSINE", "params": {"ef": 64}},
                limit=top_k,
                output_fields=["table_name", "description", "schema_text"],
            )
            hits = []
            for hits_list in results:
                for hit in hits_list:
                    hits.append({
                        "table_name": hit.entity.get("table_name"),
                        "description": hit.entity.get("description"),
                        "schema_text": hit.entity.get("schema_text"),
                        "score": hit.distance,
                    })
            return hits
        except Exception:
            return []

    def count_table_schemas(self) -> int:
        """已存储的表结构数量"""
        if not self._check_available():
            return 0
        try:
            from pymilvus import Collection
            return Collection(TABLE_SCHEMAS_COLLECTION).num_entities
        except Exception:
            return 0

    # ── knowledge_embeddings ──

    def init_knowledge_embeddings_collection(self):
        if not self._check_available():
            return
        try:
            from pymilvus import Collection, FieldSchema, CollectionSchema, DataType, utility
            if utility.has_collection(KNOWLEDGE_EMBEDDINGS_COLLECTION):
                return
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="knowledge_dict_id", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=255),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=DIM),
            ]
            schema = CollectionSchema(fields, description="Knowledge Point Embeddings")
            collection = Collection(KNOWLEDGE_EMBEDDINGS_COLLECTION, schema)
        except Exception:
            pass

    def insert_knowledge_embedding(self, knowledge_dict_id: str, name: str, embedding: list[float]):
        if not self._check_available():
            return
        from pymilvus import Collection
        self.init_knowledge_embeddings_collection()
        collection = Collection(KNOWLEDGE_EMBEDDINGS_COLLECTION)
        collection.insert([[knowledge_dict_id], [name], [embedding]])

    def flush_knowledge_embeddings(self):
        if not self._check_available():
            return
        from pymilvus import Collection
        Collection(KNOWLEDGE_EMBEDDINGS_COLLECTION).flush()

    def search_knowledge_embeddings(self, query_vector: list[float], top_k: int = 5) -> list[dict]:
        if not self._check_available():
            return []
        try:
            from pymilvus import Collection
            collection = Collection(KNOWLEDGE_EMBEDDINGS_COLLECTION)
            results = collection.search(
                data=[query_vector],
                anns_field="embedding",
                param={"metric_type": "COSINE", "params": {"ef": 64}},
                limit=top_k,
                output_fields=["knowledge_dict_id", "name"],
            )
            hits = []
            for hits_list in results:
                for hit in hits_list:
                    hits.append({
                        "knowledge_dict_id": hit.entity.get("knowledge_dict_id"),
                        "name": hit.entity.get("name"),
                        "score": hit.distance,
                    })
            return hits
        except Exception:
            return []

    def build_knowledge_index(self):
        if not self._check_available():
            return
        try:
            from pymilvus import Collection, utility
            collection = Collection(KNOWLEDGE_EMBEDDINGS_COLLECTION)
            if not utility.has_collection(KNOWLEDGE_EMBEDDINGS_COLLECTION):
                return
            # 如果已有索引则跳过
            if collection.has_index():
                if not self._is_loaded(KNOWLEDGE_EMBEDDINGS_COLLECTION):
                    collection.load()
                return
            index_params = {"metric_type": "COSINE", "index_type": "HNSW", "params": {"M": 16, "efConstruction": 200}}
            collection.create_index(field_name="embedding", index_params=index_params)
            collection.load()
        except Exception:
            pass

    def _is_loaded(self, collection_name: str) -> bool:
        try:
            from pymilvus import utility
            state = utility.loading_progress(collection_name)
            return state and state.get("loading_progress", "0%") == "100%"
        except Exception:
            return False

    def count_knowledge_embeddings(self) -> int:
        if not self._check_available():
            return 0
        try:
            from pymilvus import Collection
            return Collection(KNOWLEDGE_EMBEDDINGS_COLLECTION).num_entities
        except Exception:
            return 0

    def count(self) -> int:
        if not self._check_available():
            return 0
        try:
            from pymilvus import Collection
            return Collection(COLLECTION_NAME).num_entities
        except Exception:
            return 0
