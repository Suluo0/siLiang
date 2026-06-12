from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "agent_trace" (
    "id" UUID NOT NULL PRIMARY KEY,
    "trace_id" VARCHAR(64) NOT NULL UNIQUE,
    "user_input" TEXT NOT NULL,
    "status" VARCHAR(20) NOT NULL DEFAULT 'pending',
    "source" VARCHAR(20),
    "topic_id" VARCHAR(64),
    "topic_name" VARCHAR(255),
    "tool_calls" JSONB,
    "reasoning_chain" JSONB,
    "total_duration_ms" INT,
    "llm_call_count" INT NOT NULL DEFAULT 0,
    "errors" JSONB,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_agent_trace_trace_i_0bec53" ON "agent_trace" ("trace_id");
COMMENT ON COLUMN "agent_trace"."user_input" IS '用户原始输入';
COMMENT ON COLUMN "agent_trace"."status" IS 'pending / running / success / failed / rejected';
COMMENT ON COLUMN "agent_trace"."source" IS 'recall / generated / rejected / error';
COMMENT ON COLUMN "agent_trace"."topic_id" IS '最终生成的 topic_id';
COMMENT ON COLUMN "agent_trace"."topic_name" IS '最终 topic 名称';
COMMENT ON COLUMN "agent_trace"."tool_calls" IS '工具调用序列 [{name, args}]';
COMMENT ON COLUMN "agent_trace"."reasoning_chain" IS 'Agent 推理链';
COMMENT ON COLUMN "agent_trace"."total_duration_ms" IS '总耗时(ms)';
COMMENT ON COLUMN "agent_trace"."llm_call_count" IS 'LLM 调用次数';
COMMENT ON COLUMN "agent_trace"."errors" IS '错误记录';
COMMENT ON TABLE "agent_trace" IS 'Agent 请求追踪记录表';
CREATE TABLE IF NOT EXISTS "captcha" (
    "id" UUID NOT NULL PRIMARY KEY,
    "code" VARCHAR(8) NOT NULL,
    "used" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "captcha"."code" IS '4位验证码';
COMMENT ON COLUMN "captcha"."used" IS '是否已被使用';
COMMENT ON TABLE "captcha" IS '图形验证码';
CREATE TABLE IF NOT EXISTS "interview_persona" (
    "id" UUID NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "description" TEXT NOT NULL,
    "tags" JSONB NOT NULL,
    "personality" VARCHAR(50) NOT NULL,
    "technical_depth" INT NOT NULL DEFAULT 3,
    "communication_style" VARCHAR(50) NOT NULL,
    "difficulty_bias" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "system_prompt" TEXT NOT NULL,
    "opening_line" TEXT NOT NULL,
    "follow_up_templates" JSONB NOT NULL,
    "is_default" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "interview_persona" IS '预设面试官人设';
CREATE TABLE IF NOT EXISTS "job_position" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(50) NOT NULL,
    "category" VARCHAR(30),
    "sort_order" INT NOT NULL DEFAULT 0
);
COMMENT ON TABLE "job_position" IS '岗位';
CREATE TABLE IF NOT EXISTS "knowledge_dict" (
    "id" UUID NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "description" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "knowledge_dict" IS '知识点名称词典';
CREATE TABLE IF NOT EXISTS "knowledge_alias" (
    "id" UUID NOT NULL PRIMARY KEY,
    "alias" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "knowledge_id" UUID NOT NULL REFERENCES "knowledge_dict" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_knowledge_a_knowled_8da8f0" UNIQUE ("knowledge_id", "alias")
);
COMMENT ON TABLE "knowledge_alias" IS '知识点别名';
CREATE TABLE IF NOT EXISTS "menu" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "path" VARCHAR(255) NOT NULL,
    "icon" VARCHAR(100),
    "parent_id" INT,
    "sort_order" INT NOT NULL DEFAULT 0,
    "is_visible" BOOL NOT NULL DEFAULT True,
    "component" VARCHAR(255),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "menu"."name" IS '菜单名称';
COMMENT ON COLUMN "menu"."path" IS '路由路径';
COMMENT ON COLUMN "menu"."icon" IS '图标';
COMMENT ON COLUMN "menu"."parent_id" IS '父级菜单ID';
COMMENT ON COLUMN "menu"."sort_order" IS '排序';
COMMENT ON COLUMN "menu"."is_visible" IS '是否显示';
COMMENT ON COLUMN "menu"."component" IS '组件路径';
COMMENT ON TABLE "menu" IS '菜单模型';
CREATE TABLE IF NOT EXISTS "outbox" (
    "id" UUID NOT NULL PRIMARY KEY,
    "event_type" VARCHAR(64) NOT NULL,
    "payload" JSONB NOT NULL,
    "status" VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    "retry_count" INT NOT NULL DEFAULT 0,
    "error_message" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "processed_at" TIMESTAMPTZ
);
COMMENT ON TABLE "outbox" IS 'Outbox 补偿表 — PG 成功但 Milvus 写入失败时记录';
CREATE TABLE IF NOT EXISTS "prompt_template" (
    "id" UUID NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL UNIQUE,
    "description" TEXT,
    "system_prompt" TEXT,
    "user_prompt_template" TEXT NOT NULL,
    "version" INT NOT NULL DEFAULT 1,
    "is_active" BOOL NOT NULL DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "prompt_template"."name" IS '模板名称';
COMMENT ON COLUMN "prompt_template"."description" IS '模板描述';
COMMENT ON COLUMN "prompt_template"."system_prompt" IS '系统提示词';
COMMENT ON COLUMN "prompt_template"."user_prompt_template" IS '用户提示词模板，支持 {param} 占位符';
COMMENT ON COLUMN "prompt_template"."version" IS '版本号';
COMMENT ON COLUMN "prompt_template"."is_active" IS '是否启用';
COMMENT ON TABLE "prompt_template" IS '提示词模板配置表';
CREATE TABLE IF NOT EXISTS "prompt_call_log" (
    "id" UUID NOT NULL PRIMARY KEY,
    "trace_id" VARCHAR(64),
    "capability_id" VARCHAR(64),
    "system_prompt" TEXT,
    "user_prompt" TEXT,
    "input_params" JSONB,
    "output_content" TEXT,
    "status" VARCHAR(20) NOT NULL DEFAULT 'success',
    "error_message" TEXT,
    "duration_ms" INT,
    "model" VARCHAR(100),
    "token_input" INT,
    "token_output" INT,
    "response_id" VARCHAR(100),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "prompt_template_id" UUID REFERENCES "prompt_template" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_prompt_call_trace_i_e34bd6" ON "prompt_call_log" ("trace_id");
CREATE INDEX IF NOT EXISTS "idx_prompt_call_capabil_f5c2e6" ON "prompt_call_log" ("capability_id");
CREATE INDEX IF NOT EXISTS "idx_prompt_call_status_0c6b18" ON "prompt_call_log" ("status");
CREATE INDEX IF NOT EXISTS "idx_prompt_call_created_f9b4e1" ON "prompt_call_log" ("created_at");
COMMENT ON COLUMN "prompt_call_log"."trace_id" IS '请求级 trace_id';
COMMENT ON COLUMN "prompt_call_log"."capability_id" IS '调用的能力 ID: normalize_input / generate_topic...';
COMMENT ON COLUMN "prompt_call_log"."system_prompt" IS '系统提示词（截断）';
COMMENT ON COLUMN "prompt_call_log"."user_prompt" IS '用户提示词（截断）';
COMMENT ON COLUMN "prompt_call_log"."input_params" IS '结构化入参 JSON';
COMMENT ON COLUMN "prompt_call_log"."output_content" IS 'LLM 输出内容（截断）';
COMMENT ON COLUMN "prompt_call_log"."status" IS 'success / failed';
COMMENT ON COLUMN "prompt_call_log"."error_message" IS '错误信息';
COMMENT ON COLUMN "prompt_call_log"."duration_ms" IS '调用耗时(ms)';
COMMENT ON COLUMN "prompt_call_log"."model" IS '使用的模型';
COMMENT ON COLUMN "prompt_call_log"."token_input" IS '输入 token 数';
COMMENT ON COLUMN "prompt_call_log"."token_output" IS '输出 token 数';
COMMENT ON COLUMN "prompt_call_log"."response_id" IS 'LLM API 返回的 response_id';
COMMENT ON COLUMN "prompt_call_log"."prompt_template_id" IS '关联的提示词模板';
COMMENT ON TABLE "prompt_call_log" IS '提示词调用 + Agent 链路追踪记录表';
CREATE TABLE IF NOT EXISTS "topic" (
    "id" UUID NOT NULL PRIMARY KEY,
    "topic" VARCHAR(255) NOT NULL,
    "alias" JSONB,
    "domain" VARCHAR(100) NOT NULL,
    "tech_domain" VARCHAR(100),
    "category" VARCHAR(100),
    "tags" JSONB,
    "difficulty" INT NOT NULL DEFAULT 1,
    "mastery_level" INT NOT NULL DEFAULT 0,
    "review_count" INT NOT NULL DEFAULT 0,
    "keywords" JSONB,
    "core_summary" TEXT,
    "one_liner" VARCHAR(200),
    "core_points" TEXT,
    "detailed_explanation" TEXT,
    "agent_instructions_a" TEXT,
    "agent_instructions_b" TEXT,
    "agent_instructions_c" TEXT,
    "code_example" TEXT,
    "traps" TEXT,
    "bonuses" TEXT,
    "embedding_vector" TEXT,
    "status" VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    "last_reviewed" TIMESTAMPTZ,
    "next_review" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "topic" IS '面试题主表';
CREATE TABLE IF NOT EXISTS "topic_advanced_question" (
    "id" UUID NOT NULL PRIMARY KEY,
    "question" TEXT NOT NULL,
    "answer_hint" TEXT,
    "sort_order" INT NOT NULL DEFAULT 0,
    "topic_id" UUID NOT NULL REFERENCES "topic" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "topic_advanced_question" IS '进阶问题';
CREATE TABLE IF NOT EXISTS "topic_core_concept" (
    "id" UUID NOT NULL PRIMARY KEY,
    "importance" INT NOT NULL DEFAULT 3,
    "sort_order" INT NOT NULL DEFAULT 0,
    "knowledge_id" UUID NOT NULL REFERENCES "knowledge_dict" ("id") ON DELETE CASCADE,
    "topic_id" UUID NOT NULL REFERENCES "topic" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_topic_core__topic_i_165b78" UNIQUE ("topic_id", "knowledge_id")
);
COMMENT ON TABLE "topic_core_concept" IS '核心概念关联';
CREATE TABLE IF NOT EXISTS "topic_derivative" (
    "id" UUID NOT NULL PRIMARY KEY,
    "importance" INT NOT NULL DEFAULT 3,
    "sort_order" INT NOT NULL DEFAULT 0,
    "knowledge_id" UUID NOT NULL REFERENCES "knowledge_dict" ("id") ON DELETE CASCADE,
    "topic_id" UUID NOT NULL REFERENCES "topic" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_topic_deriv_topic_i_effc0b" UNIQUE ("topic_id", "knowledge_id")
);
COMMENT ON TABLE "topic_derivative" IS '衍生知识关联';
CREATE TABLE IF NOT EXISTS "topic_evaluation_anchor" (
    "id" UUID NOT NULL PRIMARY KEY,
    "level" VARCHAR(50),
    "question" TEXT NOT NULL,
    "expected_answer" TEXT,
    "sort_order" INT NOT NULL DEFAULT 0,
    "topic_id" UUID NOT NULL REFERENCES "topic" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "topic_evaluation_anchor" IS '评估基准';
CREATE TABLE IF NOT EXISTS "topic_extension" (
    "id" UUID NOT NULL PRIMARY KEY,
    "importance" INT NOT NULL DEFAULT 3,
    "sort_order" INT NOT NULL DEFAULT 0,
    "knowledge_id" UUID NOT NULL REFERENCES "knowledge_dict" ("id") ON DELETE CASCADE,
    "topic_id" UUID NOT NULL REFERENCES "topic" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_topic_exten_topic_i_12b9c7" UNIQUE ("topic_id", "knowledge_id")
);
COMMENT ON TABLE "topic_extension" IS '扩展延伸关联';
CREATE TABLE IF NOT EXISTS "topic_prerequisite" (
    "id" UUID NOT NULL PRIMARY KEY,
    "importance" INT NOT NULL DEFAULT 3,
    "sort_order" INT NOT NULL DEFAULT 0,
    "knowledge_id" UUID NOT NULL REFERENCES "knowledge_dict" ("id") ON DELETE CASCADE,
    "topic_id" UUID NOT NULL REFERENCES "topic" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_topic_prere_topic_i_f2ace8" UNIQUE ("topic_id", "knowledge_id")
);
COMMENT ON TABLE "topic_prerequisite" IS '前置知识关联';
CREATE TABLE IF NOT EXISTS "topic_reference" (
    "id" UUID NOT NULL PRIMARY KEY,
    "title" VARCHAR(255),
    "url" TEXT,
    "description" TEXT,
    "sort_order" INT NOT NULL DEFAULT 0,
    "topic_id" UUID NOT NULL REFERENCES "topic" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "topic_reference" IS '参考资源';
CREATE TABLE IF NOT EXISTS "topic_review_log" (
    "id" UUID NOT NULL PRIMARY KEY,
    "review_date" TIMESTAMPTZ,
    "mastery_level" INT,
    "review_duration" INT,
    "notes" TEXT,
    "topic_id" UUID NOT NULL REFERENCES "topic" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "topic_review_log" IS '复习记录';
CREATE TABLE IF NOT EXISTS "topic_similar_question" (
    "id" UUID NOT NULL PRIMARY KEY,
    "question" TEXT NOT NULL,
    "answer_hint" TEXT,
    "sort_order" INT NOT NULL DEFAULT 0,
    "topic_id" UUID NOT NULL REFERENCES "topic" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "topic_similar_question" IS '相似问题';
CREATE TABLE IF NOT EXISTS "user" (
    "id" UUID NOT NULL PRIMARY KEY,
    "username" VARCHAR(50) NOT NULL UNIQUE,
    "email" VARCHAR(100) NOT NULL UNIQUE,
    "password_hash" VARCHAR(255) NOT NULL,
    "is_active" BOOL NOT NULL DEFAULT True,
    "is_superuser" BOOL NOT NULL DEFAULT False,
    "token_version" INT NOT NULL DEFAULT 0,
    "email_verified" BOOL NOT NULL DEFAULT False,
    "verification_token" VARCHAR(64),
    "last_login" TIMESTAMPTZ,
    "membership_level" VARCHAR(20) NOT NULL DEFAULT 'free',
    "target_position" VARCHAR(100),
    "learning_preference" VARCHAR(50),
    "experience_level" VARCHAR(20),
    "today_target" INT NOT NULL DEFAULT 0,
    "preferences_filled" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "user" IS '用户基础表';
CREATE TABLE IF NOT EXISTS "interview_room" (
    "id" UUID NOT NULL PRIMARY KEY,
    "title" VARCHAR(200) NOT NULL DEFAULT '模拟面试',
    "status" VARCHAR(20) NOT NULL DEFAULT 'active',
    "persona_id" VARCHAR(64) NOT NULL,
    "target_position" VARCHAR(100) NOT NULL,
    "jd_text" TEXT,
    "resume_text" TEXT,
    "jd_analysis" JSONB,
    "resume_analysis" JSONB,
    "match_gap" JSONB,
    "total_rounds" INT NOT NULL DEFAULT 0,
    "avg_score" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "weakness_areas" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "ended_at" TIMESTAMPTZ,
    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "interview_room" IS '面试会话';
CREATE TABLE IF NOT EXISTS "interview_round" (
    "id" UUID NOT NULL PRIMARY KEY,
    "round_number" INT NOT NULL,
    "question_text" TEXT NOT NULL,
    "question_type" VARCHAR(20) NOT NULL,
    "answer_text" TEXT,
    "answer_started_at" TIMESTAMPTZ,
    "answer_duration_seconds" INT NOT NULL DEFAULT 0,
    "score_accuracy" DOUBLE PRECISION,
    "score_depth" DOUBLE PRECISION,
    "score_completeness" DOUBLE PRECISION,
    "score_clarity" DOUBLE PRECISION,
    "score_practical" DOUBLE PRECISION,
    "score_total" DOUBLE PRECISION,
    "score_reasoning" TEXT,
    "score_label" VARCHAR(20),
    "missing_points" JSONB,
    "route_decision" VARCHAR(20),
    "route_next_topic_id" UUID,
    "extracted_context" JSONB,
    "mq_status" VARCHAR(16) NOT NULL DEFAULT 'pending',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "room_id" UUID NOT NULL REFERENCES "interview_room" ("id") ON DELETE CASCADE,
    "topic_id" UUID REFERENCES "topic" ("id") ON DELETE SET NULL
);
COMMENT ON TABLE "interview_round" IS '面试中的每一轮问答';
CREATE TABLE IF NOT EXISTS "interview_summary" (
    "id" UUID NOT NULL PRIMARY KEY,
    "overall_score" DOUBLE PRECISION NOT NULL,
    "level_estimate" VARCHAR(20) NOT NULL,
    "accuracy_avg" DOUBLE PRECISION NOT NULL,
    "depth_avg" DOUBLE PRECISION NOT NULL,
    "completeness_avg" DOUBLE PRECISION NOT NULL,
    "clarity_avg" DOUBLE PRECISION NOT NULL,
    "practical_avg" DOUBLE PRECISION NOT NULL,
    "strengths" JSONB NOT NULL,
    "weaknesses" JSONB NOT NULL,
    "recommendations" JSONB NOT NULL,
    "raw_report" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "room_id" UUID NOT NULL UNIQUE REFERENCES "interview_room" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "interview_summary" IS '面试总结报告';
CREATE TABLE IF NOT EXISTS "user_level" (
    "id" UUID NOT NULL PRIMARY KEY,
    "level_name" VARCHAR(50) NOT NULL,
    "level_code" INT NOT NULL,
    "experience_min" INT NOT NULL,
    "experience_max" INT,
    "privileges" TEXT,
    "created_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "user_level" IS 'UserLevel 模型';
CREATE TABLE IF NOT EXISTS "user_profile" (
    "id" UUID NOT NULL PRIMARY KEY,
    "nickname" VARCHAR(50),
    "avatar" VARCHAR(255),
    "bio" TEXT,
    "user_id" UUID NOT NULL UNIQUE REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "user_profile" IS '用户信息表（一对一）';
CREATE TABLE IF NOT EXISTS "user_quota" (
    "id" UUID NOT NULL PRIMARY KEY,
    "topic_credits" INT NOT NULL DEFAULT 20,
    "agent_credits" INT NOT NULL DEFAULT 5,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" UUID NOT NULL UNIQUE REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "user_quota"."topic_credits" IS '面试题访问剩余次数';
COMMENT ON COLUMN "user_quota"."agent_credits" IS 'Agent 对话剩余次数';
COMMENT ON TABLE "user_quota" IS '每位用户的使用配额';
CREATE TABLE IF NOT EXISTS "user_topic_progress" (
    "id" UUID NOT NULL PRIMARY KEY,
    "mastery_level" INT NOT NULL DEFAULT 0,
    "review_count" INT NOT NULL DEFAULT 0,
    "last_reviewed" TIMESTAMPTZ,
    "next_review" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "topic_id" UUID NOT NULL REFERENCES "topic" ("id") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_user_topic__user_id_ff3e85" UNIQUE ("user_id", "topic_id")
);
COMMENT ON TABLE "user_topic_progress" IS '用户话题进度表';
CREATE TABLE IF NOT EXISTS "user_topic_status" (
    "id" UUID NOT NULL PRIMARY KEY,
    "status" VARCHAR(20) NOT NULL DEFAULT 'learning',
    "interview_proficiency" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "last_interview_score" DOUBLE PRECISION,
    "interview_count" INT NOT NULL DEFAULT 0,
    "interview_weak_points" JSONB NOT NULL,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "topic_id" UUID NOT NULL REFERENCES "topic" ("id") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_user_topic__user_id_d26714" UNIQUE ("user_id", "topic_id")
);
COMMENT ON TABLE "user_topic_status" IS '用户对题目的掌握状态';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
    "ELQC9QnyN/Szqnxwx6HmOcEjHmqebfhlJCUBLZ1LQUKfF6jW+2pRyUdlNu20edK5u/FcBz"
    "gEe05NjEleqPc1VQb6EpXVN6VB7lXcZPaKTGaFE3s8Y8+BLUryge11YDPVewBhT7dRuHa/"
    "Twl6enLnrE5Td7dtdurqcX8TuGIqElKeZrKJPyvwkjCbLycffp2gcgjzGQpjWpk4jlaavL"
    "PspyiYIJfhCrkS51h4FasJAlLmRbwMr9dIzhTFiu5/zC/m/kyWN7obfyZ4QpoCxoSBYRSl"
    "xhli1f5R8J72YrsaYWbSs91yIn1luXXm4ewky429qF4vFfU+XL1/e/3+1wNe964r6vkg9F"
    "8gTBFJt6AfpFSUOpm464KfyPddX92AINBIYWL0GIaKII9i4FEMr5e5V1Uyz3d1lEm/z9CW"
    "ZfkZQz2cMTQQPeyD72688FKz7Rv3YUpQx4oNzuq0Mg83VXVUisxOGjdwpUoLYxabC9MoTU"
    "WfLZBPRlAm/zE5h1MvhOrQaokcCrHZSzFN1AwIWl4RirUrgg82Po5SWgvzyc3Nu0n+C9IT"
    "K8W1oiPVSl6yq1afp+g34nheeOfzVNc8bW3ZqOZNeilhTvHt7cr6lWtlXWtl2dAw8Ny8TE"
    "fEopnjHPkn16YMJ6a+FGLHzyT/cP0rasW5zoBxRbB363p1UVBmaJkRhdV6cv0WCrr+RrOt"
    "/4PoO14UTv42SZ8uroz/5s2bYQxK8BKEYKPG6zELra4I9j4osm7GJUtN0kZhmjMFmdDQPi"
    "CJWnxldbDXqRMqjg8rZx+Sklj/A4LfD0lYyGMfEPwSq57maxumskpluSEd4jDNyvvKmNUs"
    "5lJmQl7owiQ1JA3PGuVGIYIVH45BsqPQ35CqZM8vScIxzdUCYW9q6K+CRmCNkpLG9IqMxE"
    "QYRLqenLFYGorkDtyqTc2ywV6kqf0Kuq/F7IXKi4vzFVr8AXZfgTkqMi41jKY59mzOTuAl"
    "rfdUO21JqvcYsDxNVWZzOXYI/rQJfm44uVu24WJDAMsSkQn0PnmXpmwWGT89lLu3qMXQ/Q"
    "acWONgmLUlqf5nbbIbSuIEP9oEG1uaBjC3PGVjcGLewIzpVmwwoJraAECF3M6D38BqaymJ"
    "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"
)
