# TopicSystem v3

> AI-Powered Interview Question Generation System with Agent Loop

基于 **LangGraph ReAct Agent** 的面试题自动生成与召回系统。Agent 自主编排 8 个原子能力（语义归一化 / 去重检查 / 知识库检索 / 双分数校验 / 题目生成 / 输出校验 / PG 写入 / Milvus 写入），通过 model-native tool calling 决策调用链路。

---

## 架构概览

```
POST /api/v3/topic/generate
  │
  ├─ MasterSession (Agent)
  │   ├─ normalize_input     ─→ LLM 语义归一化
  │   ├─ check_duplicate     ─→ L1 精确 + L2 语义去重
  │   ├─ search_knowledge    ─→ Milvus 向量检索
  │   ├─ verify_match        ─→ 双分数校验 (余弦 + LLM)
  │   ├─ generate_topic      ─→ LLM 从零生成
  │   └─ validate_output     ─→ 生成质量校验
  │
  └─ SlaveSession (写入隔离)
      ├─ save_to_postgres    ─→ PG 事务写入
      └─ save_to_milvus      ─→ Milvus 向量写入
```

### 核心设计原则

- **Capability 自举**：每个能力携带 `args_schema` + `to_langchain_tool()`，新增能力只需 `Registry.register()` 一行
- **Model-native tool calling**：Agent 通过 DeepSeek API 的 function calling 自主决定调用哪些工具，无硬编码路由
- **Master/Slave 隔离**：Master 仅持有读能力，Slave 仅持有 Master 显式授予的写能力，写入有事务边界
- **5 层防呆召回**：输入门 → 向量质量门 → 混合检索 → 双分数校验 → 出口质量门
- **全链路追踪**：`AgentTrace` (请求级) + `PromptCallLog` (每次 LLM 调用)

---

## 快速开始

### 环境要求

- Docker Desktop
- Python 3.12+（本地开发）
- DeepSeek API Key

### 启动

```bash
# 1. 配置 API Key
cp .env.example .env
# 编辑 .env: API_SECRET=sk-xxx, API_ADDRESS=https://api.deepseek.com/v1, API_MODEL=deepseek-chat

# 2. 启动全部服务 (PG + Milvus + App)
docker compose up -d

# 3. 验证
curl http://localhost:8000/ping        # {"status":"ok"}
curl http://localhost:8000/            # {"capabilities":8}
```

### API

| 端点 | 说明 |
|------|------|
| `POST /api/v3/topic/generate` | Agent Loop 生成 |
| `POST /api/v2/topic/generate` | Pipeline 生成（兼容） |
| `GET /api/v1/topic/list` | 题目列表 |
| `GET /api/v1/topic/{id}` | 题目详情 |
| `GET /ping` | 健康检查 |

```bash
# 生成面试题
curl -X POST http://localhost:8000/api/v3/topic/generate \
  -H "Content-Type: application/json" \
  -d '{"user_input": "HashMap底层实现"}'

# 输出: {"success":true, "source":"generated", "topic_name":"HashMap底层实现", ...}
```

---

## 项目结构

```
TopicSystem/
├── src/
│   ├── agentv3/                 # v3 Agent Loop 核心
│   │   ├── capability.py        # Capability 数据模型（自举）
│   │   ├── master.py            # MasterSession (Agent + tools)
│   │   ├── slave.py             # SlaveSession (写入隔离)
│   │   ├── executor.py          # ToolExecutor (运行时保护 + 落库追踪)
│   │   ├── session.py           # AgentSession + 三类预算
│   │   ├── prompt_builder.py    # 动态 Prompt 生成
│   │   ├── registry.py          # CapabilityRegistry (freeze)
│   │   ├── slave_registry.py    # Slave 白名单
│   │   ├── token_budget.py      # TokenBudget
│   │   ├── circuit_breaker.py   # 熔断器
│   │   ├── protocols.py         # ToolResult / SlaveResult / ReasoningStep
│   │   ├── permissions.py       # Permission 枚举
│   │   └── capabilities/
│   │       ├── register.py      # 8 个能力注册
│   │       ├── normalize.py     # 语义归一化
│   │       ├── duplicate.py     # L1+L2 去重
│   │       ├── search.py        # Milvus 检索
│   │       ├── verify.py        # 双分数校验
│   │       ├── generate.py      # LLM 生成
│   │       ├── validate.py      # 质量校验
│   │       └── write.py         # PG + Milvus 写入
│   ├── agent/                   # v2 Pipeline (兼容保留)
│   ├── tools/                   # 基础工具
│   │   ├── llm_client.py        # DeepSeek 统一客户端
│   │   ├── embedding.py         # bge-large-zh 编码器
│   │   └── milvus_client.py     # Milvus 客户端
│   ├── models/                  # Tortoise ORM 模型 (19 张表)
│   ├── api/                     # FastAPI 路由
│   ├── skills/                  # Skill Prompt 文件
│   ├── tracing/                 # OpenTelemetry + LangFuse
│   ├── workers/                 # Outbox 补偿消费者
│   └── config/                  # 配置管理
├── scripts/
│   ├── seed_topics_1000.json    # 996 题种子
│   └── batch_generate.py        # 批量生成脚本
├── tests/                       # pytest 测试
├── docker-compose.yml           # PG + Milvus + App
├── Dockerfile                   # App 容器化
├── requirements.txt             # pip 依赖
├── DESIGN.md                    # 技术设计文档
└── .gitignore
```

---

## 能力注册表

| ID | 名称 | Scope | Cost | 说明 |
|----|------|-------|------|------|
| `normalize_input` | 语义归一化 | read | cheap | 用户输入 → 核心概念+领域+关键词 |
| `check_duplicate` | 去重检查 | read | cheap | L1 精确匹配 + L2 语义相似度 |
| `search_knowledge` | 知识库检索 | read | cheap | Milvus 向量 + 关键词检索 |
| `verify_match` | 候选校验 | read | cheap | 余弦 + LLM 双判 |
| `generate_topic` | 题目生成 | read | expensive | LLM 从零生成完整面试题 |
| `validate_output` | 输出校验 | read | cheap | 生成内容质量检查 |
| `save_to_postgres` | PG 写入 | write | cheap | Slave only |
| `save_to_milvus` | Milvus 写入 | write | cheap | Slave only |

### 新增能力

```python
from src.agentv3.registry import CapabilityRegistry

CapabilityRegistry.register(Capability(
    id="suggest_related", name="相关推荐",
    description="根据已有面试题推荐相关题目",
    when_relevant="已获取到至少一道面试题时",
    when_irrelevant="还没有获取到题目时",
    permissions=[Permission.READ, Permission.DB_QUERY],
    scope="read", handler=suggest_related_fn,
    args_schema=SuggestArgs,  # Pydantic model
))
# Agent 自动感知，无需改任何代码
```

---

## 技术栈

| 层 | 选型 |
|----|------|
| Agent 框架 | LangGraph ReAct Agent |
| LLM | DeepSeek chat |
| Web 框架 | FastAPI |
| ORM | Tortoise ORM |
| 关系数据库 | PostgreSQL 16 |
| 向量数据库 | Milvus 2.4 |
| 容器化 | Docker + Docker Compose |
| 测试 | pytest + pytest-asyncio |

---

## 许可证

MIT
