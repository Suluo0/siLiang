# 目录结构

> **生成时间**：2026-06-12 00:06:53  
> **基于提交**：168f526（main）  
> **覆盖模块**：全部

---

## 顶层目录

```
TopicSystem/
├── src/                      # 后端源代码
├── TOPICSYSTEM_Web/          # 前端源代码（Vue 3 SPA）
├── tests/                    # 测试
├── scripts/                  # 脚本 + 种子数据
├── resource/                 # 资源文件
├── templates/                # 模板文件
├── skill/                    # Skill 定义
├── testPluin/                # 测试插件
├── pyproject.toml            # Poetry 依赖管理
├── requirements.txt          # pip 依赖
├── docker-compose.yml        # Docker Compose 全栈部署
├── Dockerfile                # 后端容器化
├── Jenkinsfile               # CI/CD 流水线
├── aerich.ini                # Aerich 数据库迁移配置
├── DESIGN.md                 # 技术设计文档（13,000+ 字）
└── README.md                 # 项目说明
```

## 源代码目录详解

### src/（后端）

| 子目录 | 职责 | 所属模块 |
|--------|------|----------|
| `agentv3/` | v3 Agent Loop 核心引擎：MasterSession、SlaveSession、Capability、Registry、Executor、熔断器、预算管理 | 面试题生成模块 |
| `agent/` | v2 兼容 Agent（LangGraph StateGraph 流水线） | 面试题生成模块 |
| `api/` | FastAPI 路由：topic V1 CRUD、topic V3 Agent 生成、健康检查、缓存 | 面试题生成模块 |
| `models/` | Tortoise ORM 数据模型（24 张表）：Topic + 9 关联表、User + 关联表、Outbox、PromptLog 等 | 面试题生成模块 + 用户模块 |
| `tools/` | 基础工具：LLM Client、Embedding Encoder、Milvus Client | 面试题生成模块 |
| `skills/` | Skill Prompt 文件（normalize_skill.md、gen_skill.md） | 面试题生成模块 |
| `config/` | Pydantic Settings 配置管理、数据库配置、LLM 配置、RabbitMQ 配置 | 共享 |
| `auth/` | JWT Token、bcrypt 密码哈希、鉴权依赖注入、认证 API | 用户与认证模块 |
| `common/` | RabbitMQ 客户端、语义错误统一响应 | 共享 |
| `tracing/` | OpenTelemetry + LangFuse 追踪（预留） | 共享 |
| `workers/` | 后台补偿消费者（预留） | 共享 |
| `service/` | JSON 输出服务（生成结果缓存） | 面试题生成模块 |
| `controller/` | 菜单控制器 | 用户模块 |
| `core/` | 核心基础（预留） | 共享 |

### TOPICSYSTEM_Web/src/（前端）

| 子目录 | 职责 |
|--------|------|
| `views/` | 页面组件：Dashboard、Topic/List、Topic/Detail、Chat、Auth/Login、User/List、User/Level、User/Center、Skill/Generate 等 |
| `components/` | 共享组件：Dashboard 子组件（HeroSection、StatsSection、TopicsCard 等） |
| `api/` | Axios 封装 + API 调用模块（request.js、topic.js、menu.js） |
| `router/` | Vue Router 配置（11 条路由） |
| `layout/` | 布局组件（MainLayout.vue） |
| `assets/` | 静态资源 |

## 关键文件速查

| 文件 | 作用 | 所属模块 |
|------|------|----------|
| `src/main.py` | FastAPI 应用入口：路由注册、中间件、数据库初始化、能力注册 | 面试题生成模块 |
| `src/agentv3/capability.py` | Capability 数据模型（自举工具定义） | 面试题生成模块 |
| `src/agentv3/registry.py` | CapabilityRegistry（注册 + freeze） | 面试题生成模块 |
| `src/agentv3/master.py` | MasterSession（Agent 编排器） | 面试题生成模块 |
| `src/agentv3/slave.py` | SlaveSession（写隔离执行器） | 面试题生成模块 |
| `src/agentv3/executor.py` | ToolExecutor（运行时保护：超时/预算/熔断/日志） | 面试题生成模块 |
| `src/agentv3/session.py` | AgentSession（三类预算：迭代/时间/Token） | 面试题生成模块 |
| `src/agentv3/capabilities/register.py` | 8 个能力注册入口 | 面试题生成模块 |
| `src/agentv3/capabilities/write.py` | PG + Milvus 双写（含 Outbox 补偿） | 面试题生成模块 |
| `src/tools/llm_client.py` | DeepSeek 统一 LLM 客户端（单例） | 面试题生成模块 |
| `src/tools/embedding.py` | bge-large-zh Embedding 编码器（单例） | 面试题生成模块 |
| `src/tools/milvus_client.py` | Milvus CRUD + 检索（单例） | 面试题生成模块 |
| `src/config/settings.py` | Pydantic BaseSettings 配置管理 | 共享 |
| `src/auth/jwt.py` | JWT Token 创建与验证 | 用户模块 |
| `src/auth/api.py` | 认证 API 端点（注册/登录/刷新/个人资料） | 用户模块 |
| `src/models/topic.py` | Topic 主表模型（19 个字段） | 面试题生成模块 |
| `src/models/user.py` | User 模型（认证 + 偏好设置） | 用户模块 |
| `TOPICSYSTEM_Web/src/router/index.js` | 前端路由配置 | 前端 |
| `docker-compose.yml` | 6 服务 Docker Compose 编排 | 部署运维 |
| `Jenkinsfile` | CI/CD 流水线定义 | 部署运维 |
