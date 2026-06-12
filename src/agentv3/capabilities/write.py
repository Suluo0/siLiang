"""
write capabilities —— Slave Session 专用
save_to_postgres (主表 + knowledge_dict + 4关联表 + evaluation/similar/advanced/reference)
save_to_milvus
"""
import asyncio
import uuid
from src.models.topic import Topic
from src.models.knowledge_dict import KnowledgeDict
from src.models.knowledge_alias import KnowledgeAlias
from src.models.topic_prerequisite import TopicPrerequisite
from src.models.topic_core_concept import TopicCoreConcept
from src.models.topic_derivative import TopicDerivative
from src.models.topic_extension import TopicExtension
from src.models.topic_evaluation_anchor import TopicEvaluationAnchor
from src.models.topic_similar_question import TopicSimilarQuestion
from src.models.topic_advanced_question import TopicAdvancedQuestion
from src.models.topic_reference import TopicReference
from src.tools.embedding import EmbeddingEncoder
from src.tools.llm_client import LLMClient
from src.tools.milvus_client import MilvusClient
from tortoise.transactions import in_transaction

# type → (model, table_name)
_KNOWLEDGE_TABLE = {
    "prerequisite": TopicPrerequisite,
    "core_concept": TopicCoreConcept,
    "derivative":   TopicDerivative,
    "extension":    TopicExtension,
}

# 固定映射表（非知识点的关联表）
_FIXED_RELATIONS = [
    (TopicEvaluationAnchor, "evaluation_anchors",
     {"level": "level", "question": "question", "expected_answer": "expected_answer"}),
    (TopicSimilarQuestion, "similar_questions",
     {"question": "question", "answer_hint": "answer_hint"}),
    (TopicAdvancedQuestion, "advanced_questions",
     {"question": "question", "answer_hint": "answer_hint"}),
    (TopicReference, "references",
     {"title": "title", "url": "url", "description": "description"}),
]


# ── 知识点去重 ──

_AUTO_DEDUP_THRESHOLD = 0.85   # cosine ≥ 0.85 → 自动同义，免 LLM
_LLM_CHECK_MIN = 0.75           # cosine ≥ 0.75 → 交 LLM 确认（如果 BGE 都给不到 0.75，基本没救了）

_SYNONYM_PROMPT = """你是一个技术概念去重专家。判断以下两个技术名词是否指向同一概念。
只回答 YES 或 NO。不解释。

例：
A: MVCC  B: 多版本并发控制 → YES
A: 哈希冲突  B: Hash Collision → YES
A: 哈希冲突  B: 红黑树 → NO
A: 事务隔离  B: 隔离级别 → NO
A: 数据库连接池  B: 连接池 → YES
"""


async def _sql_alias_lookup(name: str) -> KnowledgeDict | None:
    """Layer 1: SQL 别名精确匹配"""
    alias = await KnowledgeAlias.filter(alias=name).first().prefetch_related("knowledge")
    if alias:
        return alias.knowledge
    return None


async def _semantic_dedup(name: str, description: str | None = None) -> KnowledgeDict | None:
    """Layer 2: BGE 语义去重 → 高置信自动写 alias / 中置信 LLM 确认"""
    encoder = EmbeddingEncoder.get_instance()
    milvus = MilvusClient.get_instance()

    if not encoder.available:
        return None

    search_text = f"{name} {description}" if description else name
    vec = encoder.encode(search_text)
    milvus.build_knowledge_index()
    candidates = milvus.search_knowledge_embeddings(vec.tolist(), top_k=5)
    if not candidates:
        return None

    for c in candidates:
        # 跳过同名的（可能来自本轮插入的残留）
        if c["name"] == name:
            continue
        if c["score"] >= _AUTO_DEDUP_THRESHOLD:
            # 高置信 → 自动写 alias
            kd = await KnowledgeDict.filter(id=c["knowledge_dict_id"]).first()
            if kd:
                try:
                    await KnowledgeAlias.create(id=str(uuid.uuid4()), knowledge_id=kd.id, alias=name)
                except Exception:
                    pass
                return kd

    # 中等置信 → LLM 确认
    for c in candidates:
        if c["score"] >= _LLM_CHECK_MIN:
            llm = LLMClient.get_instance()
            prompt = f"A: {name}  B: {c['name']}"
            raw = await llm.ainvoke(query=prompt, system_prompt=_SYNONYM_PROMPT, temperature=0.0, max_tokens=10, json_mode=False)
            if raw and raw.strip().upper().startswith("YES"):
                kd = await KnowledgeDict.filter(id=c["knowledge_dict_id"]).first()
                if kd:
                    try:
                        await KnowledgeAlias.create(id=str(uuid.uuid4()), knowledge_id=kd.id, alias=name)
                    except Exception:
                        pass
                    return kd
            break  # 只确认第一个中等置信候选项

    return None


async def _sync_knowledge_embedding(kd: KnowledgeDict):
    """创建知识点后同步写入 Milvus"""
    encoder = EmbeddingEncoder.get_instance()
    if not encoder.available:
        return
    vec = encoder.encode(kd.name)
    milvus = MilvusClient.get_instance()
    milvus.insert_knowledge_embedding(str(kd.id), kd.name, vec.tolist())


async def _upsert_knowledge(name: str, description: str | None = None) -> KnowledgeDict:
    """知识点查重：精确匹配 → alias 查重 → 语义去重 → 新建"""

    # Layer 0: knowledge_dict.name 精确匹配
    existing = await KnowledgeDict.filter(name=name).first()
    if existing:
        return existing

    # Layer 1: knowledge_alias.alias 精确匹配
    alias_match = await _sql_alias_lookup(name)
    if alias_match:
        return alias_match

    # Layer 2: BGE 语义去重
    semantic_match = await _semantic_dedup(name, description)
    if semantic_match:
        return semantic_match

    # 新建知识点
    kd = await KnowledgeDict.create(id=str(uuid.uuid4()), name=name, description=description)
    await _sync_knowledge_embedding(kd)
    return kd


async def _write_knowledge_points(topic_id: str, knowledge_points: list[dict]):
    valid_kps = [(kp, kp.get("type", ""), kp.get("name", "").strip())
                 for kp in knowledge_points
                 if kp.get("name", "").strip() and kp.get("type", "") in _KNOWLEDGE_TABLE]

    # ── 并行 Layer 0 + Layer 1（同批数据互不可见，Layer 2 无意义）──
    names = [name for _, _, name in valid_kps]
    layer0_results = await asyncio.gather(*[KnowledgeDict.filter(name=n).first() for n in names])
    layer1_results = await asyncio.gather(*[_sql_alias_lookup(n) for n in names])

    # 新建知识点
    new_kds = []
    for i, ((kp, kp_type, kp_name), kd0, kd1) in enumerate(zip(valid_kps, layer0_results, layer1_results)):
        if kd0:
            kd = kd0
        elif kd1:
            kd = kd1
        else:
            kd = await KnowledgeDict.create(id=str(uuid.uuid4()), name=kp_name, description=kp.get("description"))
            new_kds.append(kd)
        await _write_single_relation(topic_id, kd, kp_type, kp, i)

    # 异步同步 embedding（不阻塞事务）
    for kd in new_kds:
        await _sync_knowledge_embedding(kd)


async def _write_single_relation(topic_id: str, kd, kp_type: str, kp: dict, idx: int):
    model_cls = _KNOWLEDGE_TABLE[kp_type]
    exists = await model_cls.filter(topic_id=topic_id, knowledge_id=kd.id).first()
    if exists:
        await model_cls.filter(id=exists.id).update(importance=kp.get("importance", 3), sort_order=idx)
    else:
        await model_cls.create(
            id=str(uuid.uuid4()), topic_id=topic_id, knowledge_id=kd.id,
            importance=kp.get("importance", 3), sort_order=idx,
        )


async def _write_fixed_relations(topic_id: str, topic_data: dict):
    """写入非知识点的 4 张关联表（evaluation / similar / advanced / reference）"""
    for model_cls, json_key, field_map in _FIXED_RELATIONS:
        items = topic_data.get(json_key, [])
        if not items:
            continue
        try:
            records = []
            for idx, item in enumerate(items):
                record = {"id": str(uuid.uuid4()), "topic_id": topic_id, "sort_order": idx}
                for db_col, json_col in field_map.items():
                    record[db_col] = item.get(json_col)
                records.append(record)
            await model_cls.bulk_create([model_cls(**r) for r in records])
        except Exception:
            pass


async def save_to_postgres(topic_data: dict) -> dict:
    topic_info = topic_data.get("topic", {})
    topic_name = topic_info.get("topic", "").strip()
    if not topic_name:
        return {"topic_id": None, "topic_name": "", "created": False, "error": "topic name 为空"}

    async with in_transaction():
        existing = await Topic.filter(topic=topic_name).first()
        if existing:
            return {"topic_id": str(existing.id), "topic_name": topic_name, "created": False}

        tid = str(uuid.uuid4())
        await Topic.create(
            id=tid, topic=topic_name,
            alias=topic_info.get("alias"),
            domain=topic_info.get("domain", "编程基础"),
            tech_domain=topic_info.get("tech_domain"),
            category=topic_info.get("category"),
            tags=topic_info.get("tags"),
            difficulty=topic_info.get("difficulty", 3),
            mastery_level=topic_info.get("mastery_level", 0),
            review_count=topic_info.get("review_count", 0),
            keywords=topic_info.get("keywords"),
            core_summary=topic_info.get("core_summary"),
            one_liner=topic_info.get("one_liner"),
            core_points=topic_info.get("core_points"),
            detailed_explanation=topic_info.get("detailed_explanation"),
            code_example=topic_info.get("code_example"),
            traps=topic_info.get("traps"),
            bonuses=topic_info.get("bonuses"),
        )

        await _write_knowledge_points(tid, topic_data.get("knowledge_points", []))
        await _write_fixed_relations(tid, topic_data)

    return {"topic_id": tid, "topic_name": topic_name, "created": True}


async def save_to_milvus(
    topic_id: str, core_concept: str, domain: str, keywords: str, difficulty: int = 3
) -> dict:
    """Slave 专用：写入 Milvus。失败时标记 Topic 状态 + 写入 Outbox 补偿。"""
    try:
        encoder = EmbeddingEncoder.get_instance()
        vector = encoder.encode(core_concept)
        milvus = MilvusClient.get_instance()
        milvus.insert(
            topic_id=topic_id, core_concept=core_concept,
            embedding=vector.tolist(), domain=domain,
            keywords=keywords, difficulty=difficulty,
        )
        return {"success": True, "compensable": False}
    except Exception as e:
        try:
            await Topic.filter(id=topic_id).update(status="MILVUS_FAILED")
        except Exception:
            pass
        try:
            from src.models.outbox import Outbox
            await Outbox.create(
                id=str(uuid.uuid4()),
                event_type="TOPIC_CREATED",
                payload={
                    "topic_id": topic_id,
                    "core_concept": core_concept,
                    "domain": domain,
                    "keywords": keywords,
                    "difficulty": difficulty,
                },
                status="PENDING",
            )
        except Exception:
            pass
        return {"success": False, "compensable": True, "error": str(e)}
