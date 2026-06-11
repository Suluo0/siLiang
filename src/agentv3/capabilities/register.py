"""
能力注册 —— 每个 Capability 自携带 args_schema
新增能力只需实例化 + register()，无需改其他任何代码
"""
from pydantic import BaseModel, Field

from src.agentv3.capability import Capability, CostTier
from src.agentv3.permissions import Permission
from src.agentv3.registry import CapabilityRegistry
from src.agentv3.slave_registry import SlaveCapabilityRegistry

from src.agentv3.capabilities.normalize import normalize_input
from src.agentv3.capabilities.search import search_knowledge
from src.agentv3.capabilities.duplicate import check_duplicate
from src.agentv3.capabilities.verify import verify_match
from src.agentv3.capabilities.generate import generate_topic
from src.agentv3.capabilities.validate import validate_output
from src.agentv3.capabilities.write import save_to_postgres, save_to_milvus


# ── 各 capability 的 args_schema ──

class NormalizeArgs(BaseModel):
    user_input: str = Field(description="用户原始输入文本")

class SearchArgs(BaseModel):
    concept: str = Field(description="核心概念")
    keywords: list[str] = Field(description="关键词列表")
    top_k: int = Field(default=5, description="返回数量")

class DuplicateArgs(BaseModel):
    concept: str = Field(description="待检查的技术概念名称")
    domain: str = Field(default="", description="技术领域（可选）")

class VerifyArgs(BaseModel):
    query_concept: str = Field(description="查询核心概念")
    query_domain: str = Field(description="查询领域")
    candidate_concept: str = Field(description="候选核心概念")
    candidate_domain: str = Field(description="候选领域")

class GenerateArgs(BaseModel):
    core_concept: str = Field(description="核心概念")
    domain: str = Field(description="技术领域")
    keywords: list[str] = Field(description="关键词")

class ValidateArgs(BaseModel):
    topic_data: dict = Field(description="生成的完整主题数据")
    expected_concept: str = Field(description="期望的概念名")


def register_all():
    if not CapabilityRegistry.is_empty():
        return

    # ── Read ──

    CapabilityRegistry.register(Capability(
        id="normalize_input", name="语义归一化",
        description="将用户自由文本结构化为核心概念+领域+关键词",
        when_relevant="输入包含可识别的技术概念时",
        when_irrelevant="输入模糊、非技术或闲聊时",
        permissions=[Permission.READ, Permission.LLM_INVOKE],
        scope="read", handler=normalize_input,
        args_schema=NormalizeArgs,
        depends_on=[],
        estimated_cost=CostTier.CHEAP, estimated_latency_ms=1500,
        fallback="raw_input",
    ))

    CapabilityRegistry.register(Capability(
        id="check_duplicate", name="去重检查",
        description="检查一个概念是否已有高度相似的题目。L1精确匹配+L2语义相似度",
        when_relevant="批量生成前、或生成新题目前",
        when_irrelevant="知识库为空时",
        permissions=[Permission.READ, Permission.DB_QUERY],
        scope="read", handler=check_duplicate,
        args_schema=DuplicateArgs,
        estimated_cost=CostTier.CHEAP, estimated_latency_ms=30,
    ))

    CapabilityRegistry.register(Capability(
        id="search_knowledge", name="知识库检索",
        description="在已有面试题知识库中检索匹配的题目",
        when_relevant="有明确核心概念且知识库可能存在数据时",
        when_irrelevant="概念模糊或知识库确认无数据时",
        permissions=[Permission.READ, Permission.DB_QUERY],
        scope="read", handler=search_knowledge,
        args_schema=SearchArgs,
        depends_on=["normalize_input"],
        estimated_cost=CostTier.CHEAP, estimated_latency_ms=50,
    ))

    CapabilityRegistry.register(Capability(
        id="verify_match", name="候选校验",
        description="对搜索返回候选进行语义匹配校验（向量+LLM双判）",
        when_relevant="search 返回候选列表时",
        when_irrelevant="候选为空时",
        permissions=[Permission.READ, Permission.LLM_INVOKE],
        scope="read", handler=verify_match,
        args_schema=VerifyArgs,
        depends_on=["search_knowledge"],
        estimated_cost=CostTier.CHEAP, estimated_latency_ms=800,
    ))

    CapabilityRegistry.register(Capability(
        id="generate_topic", name="题目生成",
        description="从零生成完整面试题数据（含topic主表+关联表JSON）",
        when_relevant="知识库无匹配时",
        when_irrelevant="已有匹配题目时",
        permissions=[Permission.READ, Permission.LLM_INVOKE],
        scope="read", handler=generate_topic,
        args_schema=GenerateArgs,
        estimated_cost=CostTier.EXPENSIVE, estimated_latency_ms=5000,
    ))

    CapabilityRegistry.register(Capability(
        id="validate_output", name="输出校验",
        description="校验生成内容的完整性、格式正确性、关键字段非空",
        when_relevant="generate_topic 结束后写入前",
        when_irrelevant="没有生成新内容时",
        permissions=[Permission.READ, Permission.LLM_INVOKE],
        scope="read", handler=validate_output,
        args_schema=ValidateArgs,
        depends_on=["generate_topic"],
        estimated_cost=CostTier.CHEAP, estimated_latency_ms=600,
    ))

    # ── Write (Slave only) ──

    CapabilityRegistry.register(Capability(
        id="save_to_postgres", name="写入PG",
        description="将生成的面试题数据写入 PostgreSQL。仅 Slave 可用。",
        when_relevant="生成新题目且通过校验后",
        when_irrelevant="没有新内容时",
        permissions=[Permission.WRITE, Permission.DB_WRITE],
        scope="write", handler=save_to_postgres,
        estimated_cost=CostTier.CHEAP, estimated_latency_ms=100,
    ))

    CapabilityRegistry.register(Capability(
        id="save_to_milvus", name="写入Milvus",
        description="将面试题向量写入 Milvus。失败不阻塞，Outbox补偿。仅 Slave 可用。",
        when_relevant="PG写入成功后",
        when_irrelevant="PG写入失败时",
        permissions=[Permission.WRITE, Permission.DB_MILVUS],
        scope="write", handler=save_to_milvus,
        depends_on=["save_to_postgres"],
        estimated_cost=CostTier.CHEAP, estimated_latency_ms=100,
    ))

    SlaveCapabilityRegistry.register("save_to_postgres", "核心写入")
    SlaveCapabilityRegistry.register("save_to_milvus", "向量写入")
