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
from src.agentv3.capabilities.query_db import query_database

from src.agentv3.capabilities.score_answer import score_answer
from src.agentv3.capabilities.extract_context import extract_context
from src.agentv3.capabilities.generate_followup import generate_followup
from src.agentv3.capabilities.analyze_resume import analyze_resume
from src.agentv3.capabilities.analyze_jd import analyze_jd
from src.agentv3.capabilities.match_resume_jd import match_resume_jd
from src.agentv3.capabilities.publish_event import publish_interview_event


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

class QueryArgs(BaseModel):
    query: str = Field(description="自然语言查询意图")
    context: str = Field(default="", description="附加上下文（如user_id等）")

class ScoreAnswerArgs(BaseModel):
    question_text: str = Field(description="面试问题文本")
    expected_key_points: list[str] = Field(description="期望包含的关键知识点")
    user_answer: str = Field(description="用户回答文本")
    question_difficulty: int = Field(default=3, description="题目难度1-5")
    persona_level: int = Field(default=3, description="面试官技术深度1-5")

class ExtractContextArgs(BaseModel):
    question_text: str = Field(description="面试问题")
    answer_text: str = Field(description="用户回答")
    scores: dict = Field(description="评分结果")

class GenerateFollowupArgs(BaseModel):
    route: str = Field(description="路由：derivative/extension/prerequisite")
    current_topic_name: str = Field(description="当前题目名称")
    current_domain: str = Field(description="当前领域")
    current_difficulty: int = Field(description="当前题目难度")
    extracted_context: dict = Field(description="提取的上下文")
    persona_level: int = Field(default=3, description="面试官技术深度")

class AnalyzeResumeArgs(BaseModel):
    resume_text: str = Field(description="简历文本")

class AnalyzeJDArgs(BaseModel):
    jd_text: str = Field(description="JD文本")

class MatchResumeJDArgs(BaseModel):
    resume_analysis: dict = Field(description="简历分析结果")
    jd_analysis: dict = Field(description="JD分析结果")

class PublishEventArgs(BaseModel):
    event_data: dict = Field(description="事件数据")


def register_all():
    if not CapabilityRegistry.is_empty():
        return

    # ── Read（ReAct Agent 用）──

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
        resource_group="llm_api",
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
        resource_group="milvus",
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
        resource_group="milvus",
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
        resource_group="llm_api",
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
        resource_group="llm_api",
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
        resource_group="llm_api",
    ))

    # ── Query ──

    CapabilityRegistry.register(Capability(
        id="query_database", name="数据库查询",
        description="将自然语言转化为SQL，在PostgreSQL中执行结构化查询。适合按条件过滤题目、查知识关联、聚合统计等场景。",
        when_relevant="用户需要按结构化条件查询时",
        when_irrelevant="用户要求生成新内容、做语义理解或闲聊时",
        permissions=[Permission.READ, Permission.DB_QUERY, Permission.LLM_INVOKE],
        scope="read", handler=query_database,
        args_schema=QueryArgs,
        estimated_cost=CostTier.CHEAP, estimated_latency_ms=200,
        resource_group="llm_api",
    ))

    # ── Write（Slave only）──

    CapabilityRegistry.register(Capability(
        id="save_to_postgres", name="写入PG",
        description="将生成的面试题数据写入 PostgreSQL。仅 Slave 可用。",
        when_relevant="生成新题目且通过校验后",
        when_irrelevant="没有新内容时",
        permissions=[Permission.WRITE, Permission.DB_WRITE],
        scope="write", handler=save_to_postgres,
        estimated_cost=CostTier.CHEAP, estimated_latency_ms=100,
        resource_group="database",
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
        resource_group="milvus",
    ))

    # ── Interview（面试系统专用，也注册以享受切面保护）──

    CapabilityRegistry.register(Capability(
        id="score_answer", name="五维评分",
        description="对用户的面试回答进行五维评分（准确性/深度/覆盖度/清晰度/实战）",
        when_relevant="用户提交面试回答后",
        when_irrelevant="面试未开始或已结束时",
        permissions=[Permission.READ, Permission.LLM_INVOKE],
        scope="read", handler=score_answer,
        args_schema=ScoreAnswerArgs,
        estimated_cost=CostTier.EXPENSIVE, estimated_latency_ms=3000,
        resource_group="llm_api",
    ))

    CapabilityRegistry.register(Capability(
        id="extract_context", name="上下文提取",
        description="从单轮面试问答中提取技能/缺口/自信度等结构化上下文信息",
        when_relevant="score_answer 完成后",
        when_irrelevant="没有评分结果时",
        permissions=[Permission.READ, Permission.LLM_INVOKE],
        scope="read", handler=extract_context,
        args_schema=ExtractContextArgs,
        estimated_cost=CostTier.CHEAP, estimated_latency_ms=1500,
        resource_group="llm_api",
    ))

    CapabilityRegistry.register(Capability(
        id="generate_followup", name="追问生成",
        description="根据评分路由（衍生/扩展/前置）生成下一道面试题",
        when_relevant="路由决策完成后",
        when_irrelevant="面试已结束时",
        permissions=[Permission.READ, Permission.LLM_INVOKE],
        scope="read", handler=generate_followup,
        args_schema=GenerateFollowupArgs,
        depends_on=["score_answer", "extract_context"],
        estimated_cost=CostTier.EXPENSIVE, estimated_latency_ms=3000,
        resource_group="llm_api",
    ))

    CapabilityRegistry.register(Capability(
        id="analyze_resume", name="简历分析",
        description="解析简历文本，提取技能/经验级别/领域/亮点",
        when_relevant="用户上传简历时",
        when_irrelevant="未提供简历时",
        permissions=[Permission.READ, Permission.LLM_INVOKE],
        scope="read", handler=analyze_resume,
        args_schema=AnalyzeResumeArgs,
        estimated_cost=CostTier.CHEAP, estimated_latency_ms=2000,
        resource_group="llm_api",
    ))

    CapabilityRegistry.register(Capability(
        id="analyze_jd", name="JD分析",
        description="解析JD文本，提取岗位/技能要求/考察领域",
        when_relevant="用户上传JD时",
        when_irrelevant="未提供JD时",
        permissions=[Permission.READ, Permission.LLM_INVOKE],
        scope="read", handler=analyze_jd,
        args_schema=AnalyzeJDArgs,
        estimated_cost=CostTier.CHEAP, estimated_latency_ms=2000,
        resource_group="llm_api",
    ))

    CapabilityRegistry.register(Capability(
        id="match_resume_jd", name="简历JD对比",
        description="对比简历和JD，输出差距分析和建议考察重点",
        when_relevant="简历和JD分析都完成后",
        when_irrelevant="缺少任一方分析时",
        permissions=[Permission.READ, Permission.LLM_INVOKE],
        scope="read", handler=match_resume_jd,
        args_schema=MatchResumeJDArgs,
        depends_on=["analyze_resume", "analyze_jd"],
        estimated_cost=CostTier.CHEAP, estimated_latency_ms=1500,
        resource_group="llm_api",
    ))

    CapabilityRegistry.register(Capability(
        id="publish_interview_event", name="面试事件发布",
        description="发布面试轮次完成事件到 MQ，触发异步处理",
        when_relevant="每轮面试结束后",
        when_irrelevant="MQ不可用时（降级到日志）",
        permissions=[Permission.WRITE],
        scope="write", handler=publish_interview_event,
        args_schema=PublishEventArgs,
        estimated_cost=CostTier.FREE, estimated_latency_ms=50,
        resource_group="mq",
    ))

    # ── Slave 白名单 ──

    SlaveCapabilityRegistry.register("save_to_postgres", "核心写入")
    SlaveCapabilityRegistry.register("save_to_milvus", "向量写入")
