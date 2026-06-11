"""
DUAL_WRITE 节点 — 双写 PG + Milvus
主路径: PostgreSQL 事务写入
副路径: Milvus 向量写入（失败不阻塞）
"""
import uuid
from src.agent.state import AgentState, AgentStatus, record_transition
from src.tools.embedding import EmbeddingEncoder
from src.tools.milvus_client import MilvusClient
from src.models.topic import Topic
from tortoise.transactions import in_transaction


async def dual_write_node(state: AgentState) -> AgentState:
    record_transition(state, AgentStatus.DUAL_WRITING, "开始双写 PG + Milvus")

    topic_data = state.get("generated_topic")
    if not topic_data:
        state["errors"].append({"node": "dual_write", "error": "生成数据为空"})
        state["status"] = AgentStatus.ERROR
        return state

    topic_info = topic_data.get("topic", {})
    topic_name = topic_info.get("topic", "").strip()
    if not topic_name:
        state["errors"].append({"node": "dual_write", "error": "topic name 为空"})
        state["status"] = AgentStatus.ERROR
        return state

    normalized = state.get("normalized", {})
    core_concept = normalized.get("core_concept", topic_name)
    keywords_str = ",".join(normalized.get("keywords", []))
    domain = topic_info.get("domain", "编程基础")
    topic_id = str(uuid.uuid4())

    # ── 1. PostgreSQL 事务写入 ──
    try:
        async with in_transaction():
            existing = await Topic.filter(topic=topic_name).first()
            if existing:
                state["topic_id"] = str(existing.id)
                state["verdict"] = "HIT"
                record_transition(state, AgentStatus.WRITTEN, f"Topic 已存在: {topic_name}")
                return state

            await Topic.create(
                id=topic_id,
                topic=topic_name,
                alias=topic_info.get("alias"),
                domain=domain,
                category=topic_info.get("category"),
                tags=topic_info.get("tags"),
                difficulty=topic_info.get("difficulty", 3),
                mastery_level=topic_info.get("mastery_level", 0),
                review_count=topic_info.get("review_count", 0),
                keywords=topic_info.get("keywords"),
                core_summary=topic_info.get("core_summary"),
                core_points=topic_info.get("core_points"),
                detailed_explanation=topic_info.get("detailed_explanation"),
                code_example=topic_info.get("code_example"),
            )

        state["topic_id"] = topic_id
    except Exception as e:
        state["errors"].append({"node": "dual_write", "pg_error": str(e)})
        state["status"] = AgentStatus.ERROR
        return state

    # ── 2. Milvus 写入（非阻塞）──
    try:
        encoder = EmbeddingEncoder.get_instance()
        vector = encoder.encode(core_concept)
        milvus = MilvusClient.get_instance()
        milvus.insert(
            topic_id=topic_id,
            core_concept=core_concept,
            embedding=vector.tolist(),
            domain=domain,
            keywords=keywords_str,
            difficulty=topic_info.get("difficulty", 3),
        )
    except Exception as e:
        state["errors"].append({"node": "dual_write", "milvus_error": str(e), "compensable": True})

    record_transition(state, AgentStatus.WRITTEN, f"topic_id={topic_id}")
    return state
