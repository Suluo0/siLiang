# 测试策略

> **生成时间**：2026-06-12 00:06:53  
> **基于提交**：168f526（main）  
> **覆盖模块**：全部

---

## 测试框架

| 类型 | 框架 | 版本 |
|------|------|------|
| 单元测试 | pytest | >=8.0 |
| 异步测试 | pytest-asyncio | >=0.24 |
| HTTP 测试 | httpx | >=0.27 |

## 测试覆盖率

| 模块 | 是否有测试 | 测试文件 | 测试类型 |
|------|-----------|----------|----------|
| Agent v3 引擎 | 是 | `test_agentv3.py` | 单元测试 + Golden Dataset 回归 |
| Topic CRUD | 是 | `test_topic_crud.py` | 单元测试（模型） |
| User CRUD | 是 | `test_user_crud.py` | 单元测试（模型） |
| UserLevel CRUD | 是 | `test_user_level_crud.py` | 单元测试（模型） |
| TopicService | 是 | `test_topic_save.py` | 集成测试（JSON fixture） |
| TopicAPI | 是 | `test_topic_api_flow.py` | 集成测试 |
| 端到端生成 | 是 | `test_api_with_json.py` | 集成测试（JSON fixture，跳过 LLM） |
| 工具体层 | 否 | — | LLM/Embedding/Milvus 未直接测试（可选依赖） |
| 前端 | 否 | — | Vue 组件未覆盖 |
| Auth 认证 | 否 | — | 未直接测试 |
| Workers | 否 | — | 未实现 |

### `test_agentv3.py` 三层结构（253 行）

1. **Unit**: `CapabilityRegistry`（register/filter/idempotent/freeze）、`SlaveRegistry`（白名单）、`TokenBudget`（consume/low）、`CircuitBreaker`（open/half-open）、`SlaveSession`（拒绝 read/非白名单）、`Capability` 模型（format_for_prompt）
2. **Protection**: `ToolExecutor`（precondition 拦截、timeout 保护）
3. **Golden Dataset 回归**: 5 个参数化用例通过 `TestClient` 调用完整 Agent 流程——`HashMap底层实现`（success）、`MySQL事务`（rejected）、`今天天气怎么样`（rejected）、`CAP定理`（success）、`a`（rejected）

## 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行 Agent v3 测试
pytest tests/test_agentv3.py -v

# 跳过 Golden Dataset（不依赖 DeepSeek API，适合 CI）
pytest tests/test_agentv3.py -v -k "not GoldenDataset"

# 运行特定模型测试
pytest tests/test_topic_crud.py -v
pytest tests/test_user_crud.py -v

# 运行覆盖率报告
pytest tests/ -v --cov=src --cov-report=term-missing
```

## 测试约定

| 约定 | 说明 |
|------|------|
| 测试文件命名 | `test_*.py` 前缀 |
| 测试函数命名 | `test_<功能描述>` |
| 异步测试 | 所有测试函数使用 `async def` + `pytest-asyncio` |
| Fixture | `conftest.py` 提供 `setup_db` fixture：function 作用域，每次测试连接真实 PG |
| Fixture 数据 | `test_topic_save.py` 从 `src/service/json_output/` 读取历史 LLM 输出 JSON 作为 fixture |
| Mock 策略 | **不使用 Mock**——所有测试直接连接本地 PostgreSQL `postgres://postgres:Xswl1139@localhost:5432/topic` |
| LLM 调用 | Golden Dataset 测试调用真实 DeepSeek API；其他测试通过 JSON fixture 文件跳过 LLM |
| CI 集成 | `Jenkinsfile` 中 Golden Dataset 被跳过（`-k "not GoldenDataset"`），失败被允许（`|| true`） |

## 测试数据管理

- **测试数据库**：复用本地开发数据库 `topic`（无独立测试数据库隔离）
- **种子数据**：`tests/` 目录无独立 seed，依赖数据库中已有数据
- **Fixture 文件**：`src/service/json_output/` 下 4 个 JSON 文件（HashMap、红黑树、响应式布局、MySQL 事务隔离级别），由历史 LLM 生成保存，用于离线测试 `TopicService.save_topic()`

## 已知测试缺口

- 前端（Vue 3）组件无任何自动化测试
- Auth 认证流程（JWT、注册、登录）无直接单元测试
- Tool 工具层（LLMClient、EmbeddingEncoder、MilvusClient）无测试（可选依赖，通过参数化集成测试间接覆盖）
- Worker Outbox 补偿消费者未实现，因此无相关测试
- 无 E2E 测试框架配置
