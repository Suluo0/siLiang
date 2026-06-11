"""
提示词调用 + Agent 链路追踪记录表
每次 LLM 调用 / tool 执行都有日志可查
"""
from tortoise import fields
from tortoise.models import Model


class PromptCallLog(Model):
    """每次 LLM 调用的完整记录"""

    id = fields.UUIDField(pk=True)

    # 链路追踪
    trace_id = fields.CharField(max_length=64, null=True, index=True, description="请求级 trace_id")
    capability_id = fields.CharField(max_length=64, null=True, description="调用的能力 ID: normalize_input / generate_topic...")

    # 关联模板（可选——agent 调用不一定有模板）
    prompt_template = fields.ForeignKeyField(
        "models.PromptTemplate", related_name="call_logs", null=True,
        description="关联的提示词模板",
    )

    # 输入输出
    system_prompt = fields.TextField(null=True, description="系统提示词（截断）")
    user_prompt = fields.TextField(null=True, description="用户提示词（截断）")
    input_params = fields.JSONField(null=True, description="结构化入参 JSON")
    output_content = fields.TextField(null=True, description="LLM 输出内容（截断）")

    # 调用状态
    status = fields.CharField(max_length=20, default="success", description="success / failed")
    error_message = fields.TextField(null=True, description="错误信息")

    # 调用统计
    duration_ms = fields.IntField(null=True, description="调用耗时(ms)")
    model = fields.CharField(max_length=100, null=True, description="使用的模型")
    token_input = fields.IntField(null=True, description="输入 token 数")
    token_output = fields.IntField(null=True, description="输出 token 数")

    # LLM 响应元数据
    response_id = fields.CharField(max_length=100, null=True, description="LLM API 返回的 response_id")

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "prompt_call_log"
        table_description = "提示词调用 + Agent 链路追踪记录表"
        indexes = [("trace_id",), ("capability_id",), ("status",), ("created_at",)]


class AgentTrace(Model):
    """每次 Agent 请求的顶层追踪记录"""

    id = fields.UUIDField(pk=True)
    trace_id = fields.CharField(max_length=64, unique=True, index=True)
    user_input = fields.TextField(description="用户原始输入")
    status = fields.CharField(max_length=20, default="pending", description="pending / running / success / failed / rejected")
    source = fields.CharField(max_length=20, null=True, description="recall / generated / rejected / error")
    topic_id = fields.CharField(max_length=64, null=True, description="最终生成的 topic_id")
    topic_name = fields.CharField(max_length=255, null=True, description="最终 topic 名称")

    # 工具调用摘要
    tool_calls = fields.JSONField(null=True, description="工具调用序列 [{name, args}]")
    reasoning_chain = fields.JSONField(null=True, description="Agent 推理链")

    # 性能
    total_duration_ms = fields.IntField(null=True, description="总耗时(ms)")
    llm_call_count = fields.IntField(default=0, description="LLM 调用次数")

    # 错误
    errors = fields.JSONField(null=True, description="错误记录")

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "agent_trace"
        table_description = "Agent 请求追踪记录表"
