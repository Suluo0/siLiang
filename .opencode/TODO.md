# TopicSystem 项目总结与后续计划

> 生成时间：2026-06-16 | 测试：130/130 PASSED | 线上：926 道题目

---

## 一、已完成事项

### 1.1 架构重构

| 事项 | 状态 |
|------|------|
| AOP 切面统一切面入口：`CapabilityRegistry.execute()/call()` 提供超时/熔断/日志/耗时全线保护 | ✅ |
| 中间件拆分：`main.py` 142L→67L，auth/quota 独立为 `middleware/` 模块 | ✅ |
| LLM 配置归一：`llm_config.py` 为单一来源，`LLMClient`/`master.py` 统一走 Registry | ✅ |
| PUBLIC_PATHS 收敛到 `auth/deps.py` 单源 | ✅ |
| `controller/`→`api/`，`cache.py`→`common/`，`database_db.py`→`aerich_config.py` | ✅ |
| `src/utils/` 提取重复函数（cosine/parse_keywords/clean_json/load_skill） | ✅ |
| ContextVar 上下文传递：`current_trace_id`/`current_caller`/`current_budget` | ✅ |
| ToolExecutor 自动从 ContextVar 读 trace_id，不再外部传入 | ✅ |
| TokenBudget + CircuitBreaker 按 `resource_group` 分组熔断 | ✅ |

### 1.2 死代码清理

| 删除项 | 行数 |
|--------|------|
| `src/agent/` v1 agent 管道（8 文件） | ~682L |
| `src/api/topic_api_v2.py` | 52L |
| `src/api/topic_api_v3.py` | 58L |
| `skill/` 根目录旧技能模板 | ~200L |
| `testPluin/` 目录 | 138L |
| `src/skills/gen_skill.md` | 120L |
| `topic_api.py` 冗余 router + DetailResponse | 24L |
| `api/__init__.py` unused re-exports | 4L |
| `auth/api.py` unused imports | 2L |
| `milvus_client.py` 不可达重复代码 | 7L |
| 路由前缀 `/v1`→`/api` 统一 | 全链路 |

### 1.3 模拟面试子系统

| 能力 | 文件 |
|------|------|
| 4 个数据模型 | `interview_persona/room/round/summary.py` |
| 五维评分引擎（LLM） | `capabilities/score_answer.py` |
| 上下文提取 + 聚合 | `capabilities/extract_context.py` |
| 路由决策（derivative/extension/prerequisite） | `interview/router.py` |
| 追问生成 3 种 | `capabilities/generate_followup.py` + `skills/followup_*.md` |
| 10 套面试官人设 | `skills/persona/*.md` |
| PersonaManager 加载/编译/缓存 | `interview/persona.py` |
| InterviewSession 状态机 | `interview/session.py` |
| resume/JD/match 3 个 Capability | `capabilities/analyze_*.py` |
| MQ 事件发布 | `capabilities/publish_event.py` |
| Interview API（start/answer/summary/personas） | `api/interview_api.py` |
| 前端 Interview 三阶段页面 | `views/Interview/index.vue` |

### 1.4 掌握度评测系统（无 LLM）

| 能力 | 文件 |
|------|------|
| MasteryAttempt 记录表 | `models/mastery_attempt.py` |
| UserTopicStatus 扩展 3 字段 | `models/user_topic_status.py` |
| 五维无 LLM 评分引擎 | `capabilities/mastery_check.py` |
| API：`POST /{topic_id}/mastery-check` | `api/topic_api.py` |
| 测试：24 个用例 | `tests/test_mastery.py` |

### 1.5 去重系统

| 层级 | 方法 | 阈值 |
|------|------|------|
| L1 | PG 精确 name 匹配 | exact |
| L2 | Milvus 余弦检索 | ≥0.75 阻断 |
| L3 | Agent 双分数校验（余弦+LLM） | 0.55~0.75 触发 |
| L4 | Agent 回退 | 余弦≥0.65 阻断 |
| L5 | 名称语义（子串/共享词≥70%） | expand 阶段 |
| L6 | 后缀归一（去"——源码分析"等） | expand 阶段 |
| L7 | 内容去重（one_liner 编码查 Milvus） | ≥0.75 跳过 |

### 1.6 自迭代知识覆盖引擎

| 能力 | 文件 |
|------|------|
| 知识地图（19 领域 × 411 知识点） | `scripts/knowledge_map.json` |
| 覆盖率分析 | `scripts/iterative_coverage.py` |
| 缺口优先级排序 | 重要性 × (1-领域覆盖率) |
| 双循环：外循环选种子 + 内循环发散生成 | 同上 |
| 去重分析工具 | `scripts/dedup_analyzer.py` |

### 1.7 测试体系

| 文件 | 测试数 | 覆盖 |
|------|--------|------|
| `test_auth_api.py` | 11 | 注册/登录/refresh/公开路径 |
| `test_auth_middleware.py` | 6 | JWT校验/截断/PUBLIC_PATHS |
| `test_quota.py` | 4 | 配额扣减/403/列表不消耗 |
| `test_interview.py` | 34 | 路由/评分/Persona/Session/Model/Capability |
| `test_interview_api.py` | 6 | 人设列表/start/answer/summary |
| `test_cache.py` | 9 | TTLCache get/set/TTL/LRU/JSON |
| `test_dedup.py` | 8 | L1~L7 七层防呆阈值 |
| `test_infra.py` | 10 | TokenBudget + CircuitBreaker |
| `test_json_truncation.py` | 5 | 200字符硬切割+JSON闭合 |
| `test_model_crud.py` | 12 | 7个未测试Model CRUD |
| `test_mastery.py` | 24 | LCS/编辑距离/模糊匹配/API/Model |
| **总计** | **130** | **100% PASSED** |

### 1.8 前端优化

| 事项 | 状态 |
|------|------|
| 题库详情页重构：补充 one_liner/tech_domain/keywords/evaluation_anchors 展示 | ✅ |
| 题库列表页 Tag 过滤：去除 LFU/LRU 等纯大写短缩写 | ✅ |
| Interview 面试三步页面入口开放 | ✅ |
| 路由前缀 `/v1`→统一 | ✅ |
| 模拟面试页从 "Coming Soon" 到已开放 | ✅ |

### 1.9 鉴权与安全

| 事项 | 状态 |
|------|------|
| 未登录访客截断（all content fields → locked） | ✅ |
| 200字符硬切割 + JSON 补全闭合 | ✅ |
| quota_exhausted 标记恢复（拆分 middleware 时的遗漏 bug） | ✅ |
| PUBLIC_PATHS 收敛到单源 | ✅ |
| 服务器 .env 密钥外部化 | ✅ |

---

## 二、待完成事项

### 2.1 高优先级（P0）

| # | 事项 | 说明 |
|---|------|------|
| 1 | **题库冲刺 1000** | 当前 926 道，差 74 道。`direct_gen.py` 仍在跑 |
| 2 | **Jenkins CI/CD 恢复** | 服务器无 Jenkins 在跑。需部署 Jenkins 或改用 GitHub Actions |
| 3 | **Aerich 迁移流水线化** | 当前手动 ALTER TABLE，需切换到 `aerich migrate && aerich upgrade` |
| 4 | **Outbox Worker 上线** | `src/workers/outbox_worker.py` 已写但未运行。Milvus 写入失败数据会丢失 |

### 2.2 中优先级（P1）

| # | 事项 | 说明 |
|---|------|------|
| 5 | **RabbitMQ 接入** | `src/common/rabbitmq.py` 已完善但未接入业务流程 |
| 6 | **MQ Consumer 面试异步处理** | `publish_interview_event` 已有发布端，Consumer 未跑 |
| 7 | **OpenTelemetry/Langfuse 链路追踪** | `src/tracing/` 空目录，依赖已装，配置已有，缺 0 行实现 |
| 8 | **前端面试页全链路测试** | 现在只有后端 API 测试，前端到后端全链路未跑 |
| 9 | **上线掌握度前端 UI** | mastery-check API 已上线，前端答题+结果展示页未做 |
| 10 | **面试真人设接入** | 10 套 Persona 作为属性模板写着，但 InterviewSession 没实际使用它们 |

### 2.3 低优先级（P2）

| # | 事项 | 说明 |
|---|------|------|
| 11 | **Rate Limiting 中间件** | 登录/注册无暴力破解保护 |
| 12 | **健康检查强化** | `/ping` 不验证 DB/Milvus/LLM 连通性 |
| 13 | **11 个 standalone 脚本转 pytest** | 不可 CI，`test_agentv3.py` 等用 `if __name__` 模式 |
| 14 | **GitHub Actions CI** | pyproject.toml 已配置但无 `.github/workflows/test.yml` |
| 15 | **性能测试 locust** | 无压测脚本 |
| 16 | **Redis 会话存储** | `interview_api.py` 用内存 dict 存 session，重启即丢失 |
| 17 | **`sql/admin` 端点** | 无后台管理界面 |

### 2.4 技术债（P3）

| # | 事项 | 说明 |
|---|------|------|
| 18 | **单例改依赖注入** | LLMClient/MilvusClient/EmbeddingEncoder 三处全局单例 |
| 19 | **`generate_schemas=True` 移除** | 与 aerich 冲突，需在 Docker CMD 改为 aerich migrate |
| 20 | **前端 dist 构建自动化** | 当前手动 `scp dist/*` 到 Nginx |
| 21 | **Pydantic V2 ConfigDict 迁移** | `menu_api.py` 等仍用 class-based Config |
| 22 | **Milvus ORM API → MilvusClient 迁移** | PyMilvus 3.1 将移除旧 ORM API |

---

## 三、服务器当前状态

```
siliang-app        Up 2h      ← FastAPI + LangGraph
siliang-milvus     Up 5d      ← 向量检索
siliang-pg         Up 5d      ← PostgreSQL 16
siliang-etcd       Up 5d      ← Milvus 元数据
siliang-minio      Up 5d      ← Milvus 对象存储

DB 题目: 926 道  覆盖率: 86.4%
测试: 130/130 PASSED
API: /ping /api/topic/* /api/interview/* /api/auth/* 全部在线
```

## 四、快速启动

```bash
# 本地开发
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
cd TOPICSYSTEM_Web && npx vite --host 0.0.0.0 --port 5173

# 测试
pytest tests/ -v -m "not slow"

# 服务器部署
rsync -avz . root@115.190.161.132:/opt/siLiang/
ssh root@115.190.161.132 "docker restart siliang-app"

# 题库生成
ssh root@115.190.161.132 "docker exec -w /app siliang-app python3 scripts/iterative_coverage.py"
```
