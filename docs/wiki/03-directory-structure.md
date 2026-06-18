# 目录结构

> **生成时间**：2026-06-18 15:04:06
> **基于提交**：`7648ad3`(main)

---

## 顶层目录

```
TopicSystem/
├── src/                          # 后端源码 (100 个 .py)
├── tests/                        # 单元/集成测试 (20 个 .py)
├── scripts/                      # 长跑脚本 + 手动测试归档
│   └── manual_tests/             # 5 个 benchmark 脚本(从 tests/ 迁出)
├── migrations/                   # aerich 数据库迁移
├── TOPICSYSTEM_Web/              # Vue 3 前端
├── relay-server/                 # WebSocket 中继(仅本地,未提交) — 实时面试通信
├── docs/                         # 项目文档
│   ├── wiki/                     # ★ 本 Repo Wiki (15 份 markdown)
│   ├── TODO.md                   # 任务清单(从 .opencode/ 迁来)
│   ├── diff-local-vs-server.md   # 本地 vs 服务器代码差异报告
│   └── data-sync-plan.md         # 数据同步可行性方案
├── docker-compose.yml            # 本地 dev compose
├── docker-compose.server.yml     # 线上 server compose(siliang-* 容器)
├── Dockerfile                    # 后端镜像
├── Jenkinsfile                   # CI 配置(老,GitHub Actions 是主)
├── .github/workflows/test.yml    # GitHub Actions: pytest + cov
├── Makefile                      # 14 个目标:test/cov/lint/setup-test-db
├── .pre-commit-config.yaml       # ruff + detect-secrets
├── pyproject.toml                # Python 项目元数据 + pytest 配置 + cov 阈值
├── requirements.txt              # 锁定版本(本地)
├── aerich.ini                    # aerich migration 入口
├── .env / .env.example / .env.test / .env.test.example  # 三层环境
└── DESIGN.md                     # 早期架构方案稿(50+ KB,历史参考)
```

## src/ 后端源码

| 子目录 | 职责 | 关键文件 | 所属模块 |
|---|---|---|---|
| `src/api/` | HTTP 端点 | `topic_api.py` 386L、`interview_api.py` 174L、`menu_api.py`、`healthcheck.py` | API 层 |
| `src/auth/` | 认证 | `api.py` 310L (8 端点)、`jwt.py`、`deps.py`、`hash.py` | 用户认证 |
| `src/middleware/` | 中间件 | `auth.py` 54L、`quota.py` 37L | 横切关注点 |
| `src/agentv3/` | Agent v3(主版本) | `master.py` 292L、`registry.py`、`capability.py`、`circuit_breaker.py`、`permissions.py`、`token_budget.py`、`session.py`、`prompt_builder.py` | Agent 编排 |
| `src/agentv3/capabilities/` | 17 个原子能力 | `register.py` 310L (注册中心)、`generate.py`、`search.py`、`verify.py`、`score_answer.py`、`extract_context.py`、`generate_followup.py`、`analyze_resume.py`、`analyze_jd.py`、`match_resume_jd.py`、`mastery_check.py`、`publish_event.py`、`query_db.py` 等 | 能力实现 |
| `src/agentv3/interview/` | 模拟面试 | `session.py` 196L (面试 Loop)、`router.py` (评分→路由)、`persona.py` (面试官风格) | 面试子系统 |
| `src/agent/` | ⚠️ 旧 LangGraph 实现 | `graph.py`、`nodes/{generate,verify,recall,respond,normalize,dual_write}.py` | **已废弃,待删** |
| `src/models/` | Tortoise ORM 模型(30 张表) | `topic.py` + 8 张子表、`user.py` + 5 张关联、`interview_{persona,room,round,summary}.py`、`mastery_attempt.py`、`knowledge_dict/alias.py`、`outbox.py`、`prompt_call_log.py` (含 AgentTrace) | 数据模型 |
| `src/config/` | 配置单源 | `settings.py` (pydantic-settings)、`database.py` (Tortoise lifespan)、`llm_config.py` (LLM 配置) | 基础设施 |
| `src/tools/` | 第三方驱动封装 | `llm_client.py`、`embedding.py`、`milvus_client.py`、`schema_manager.py` | 基础设施 |
| `src/common/` | 共享工具 | `cache.py`、`rabbitmq.py`、`__init__.py` | 共享 |
| `src/workers/` | 后台 Worker | `outbox_worker.py` 146L (补偿) | 后台进程 |
| `src/utils/` | 工具函数 | `context.py` (ContextVar)、`mail.py` (SMTP) | 共享 |
| `src/tracing/` | Langfuse 追踪 | `__init__.py` | 基础设施 |
| `src/skills/` | LLM Prompt 模板 | `extract_context.md` 等 | LLM Prompt |
| `src/main.py` | ASGI 入口 | 75L:注册路由 + 中间件 + lifespan | 入口 |

## tests/ 测试目录

| 文件 | 职责 | 是否跑 e2e |
|---|---|---|
| `conftest.py` | env 注入 + topic_test 防呆 + Tortoise fixture + autouse mock LLM/SMTP/JWT | — |
| `factories.py` | factory_boy 风格 fixtures | — |
| `test_topic_crud.py` | topic + 8 子表 CRUD(9 个 schema-drift 用例标 xfail) | 否 |
| `test_agentv3.py` | capability registry / golden dataset(标 e2e+slow,默认 deselect) | 部分 |
| `test_auth_api.py` 130L | 注册/登录/验证码/refresh/me/change-password 全套 | 否 |
| `test_auth_middleware.py` 79L | JWT 中间件单元 | 否 |
| `test_cache.py` 82L | common/cache.py | 否 |
| `test_dedup.py` 104L | duplicate capability | 否 |
| `test_infra.py` 102L | settings + database + llm_config | 否 |
| `test_interview_api.py` 88L | /start /answer /summary /personas | 否 |
| `test_json_truncation.py` 73L | LLM 输出 JSON 截断容错 | 否 |
| `test_mastery.py` 203L | mastery_attempt + 五维评分 | 否 |
| `test_model_crud.py` 194L | 模型批量 CRUD 烟雾 | 否 |
| `test_quota.py` 50L | 配额扣减 | 否 |
| `test_db_write.py` | Outbox 双写,标 e2e+slow | 是 |
| `test_knowledge_dedup.py` | 知识词典去重(Milvus 不可用时 skip) | 是 |

## scripts/ 脚本

| 文件 | 职责 |
|---|---|
| `expand_topics.py` | 从已有题反向扩展前置/衍生 |
| `iterative_coverage.py` | 按知识图谱覆盖率反向补题 |
| `long_run_gen.py` | 长跑批量生成(checkpoint 续跑) |
| `dedup_analyzer.py` | 离线分析重复题 |
| `knowledge_map.json` | 知识图谱数据 |
| `manual_tests/` | 5 个手动 smoke benchmark(`api_test`/`profile_upsert*`/`single_topic_test`/`full_pipeline_test`),不参与 pytest |

## 关键文件速查

| 文件 | 作用 | 备注 |
|---|---|---|
| `src/main.py` | ASGI 入口 | 5 个 `app.include_router()` |
| `src/agentv3/capabilities/register.py` | 16 个 capability 集中注册 | **新增能力只改这一处** |
| `src/agentv3/master.py` | 出题主控编排 | 292 L 是核心 |
| `src/agentv3/interview/session.py` | 面试一轮的完整状态机 | 196 L |
| `src/middleware/auth.py` + `auth/deps.py` | JWT 中间件 + Depends | PUBLIC_PATHS 在 `auth/deps.py` 单源 |
| `src/config/settings.py` | 唯一配置入口 | 红线 1.2:禁止散落 `os.getenv` |
| `src/config/database.py` | Tortoise lifespan | 红线 2.1 |
| `tests/conftest.py` | 测试基础设施 | 防呆 + autouse mock |
| `Makefile` | 14 个目标 | `make test` / `make cov` 是常用 |
| `pyproject.toml` | pytest+cov+ruff 配置 | `[tool.pytest.ini_options]` 默认 deselect e2e/slow |
