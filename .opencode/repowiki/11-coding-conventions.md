# 编码规范

> **生成时间**：2026-06-12 00:06:53  
> **基于提交**：168f526（main）  
> **覆盖模块**：全部

---

## 代码风格

| 方面 | 规范 |
|------|------|
| 缩进 | 4 空格（Python） |
| 引号 | 双引号 `"` 用于字符串 |
| 命名风格 | snake_case（函数/变量/模块）、PascalCase（类）、UPPER_CASE（常量） |
| 行长度 | 未强制限制，但遵循可读性原则 |
| 类型注解 | 使用 Python 3.12+ 原生类型语法（`list[str]`、`str | None`） |

## 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 文件名 | snake_case | `llm_client.py`、`prompt_builder.py`、`circuit_breaker.py` |
| 变量 | snake_case | `topic_id`、`slave_grants`、`trace_id` |
| 函数 | snake_case（async 函数加 `async`） | `async normalize_input()`、`def encode()`、`def register()` |
| 类 | PascalCase | `MasterSession`、`CapabilityRegistry`、`ToolExecutor`、`CircuitBreaker` |
| 常量 | UPPER_CASE | `SYSTEM`（prompt 模板）、`PUBLIC_PATHS`、`NL_MATCH_PROMPT` |
| Pydantic 模型 | PascalCase + 语义名 | `NormalizedQuery`、`GenerateRequest`、`RecallCandidate` |
| Tortoise 模型 | PascalCase（类名）+ snake_case（表名） | `Topic` → 表 `topic`、`UserQuota` → 表 `user_quota` |

## 项目特有的约定

### import 风格
- 使用绝对导入：`from src.tools.llm_client import LLMClient`
- 延迟导入：`topic_api.py` 的 Handler 函数体内部才 `from src.models.topic import Topic`（避免循环依赖）
- 类型检查导入：`from __future__ import annotations` 未使用

### Dataclass 使用
- `@dataclass` 用于纯数据结构：`Capability`、`AgentSession`、`ToolResult`、`SlaveResult`
- Pydantic `BaseModel` 用于需要校验的结构：`NormalizedQuery`、`GenerateRequest`、`Settings`

### 单例模式
- 工具层的三个客户端均使用单例 + 类级 `_instance`：
  ```python
  LLMClient.get_instance()
  EmbeddingEncoder.get_instance()
  MilvusClient.get_instance()
  ```
- 使用 `reset()` 方法支持测试中强制重新加载

### 优雅降级
- `EmbeddingEncoder.encode()` 在模型不可用时返回零向量，不抛异常
- `MilvusClient` 所有方法在连接失败时返回空结果
- `check_duplicate` 的 L2 语义去重在 Milvus 不可用时降级为 L1 only

### 能力注册模式
- 新增能力仅需：1) 写 handler 函数、2) 定义 args_schema、3) `CapabilityRegistry.register()`
- `register_all()` 检查 `is_empty()` 确保幂等
- 启动后调用 `freeze()` 锁定注册表

### 前端规范
- Vue 3 Composition API（`<script setup>`）
- Element Plus 组件库 + 中文语言包
- Axios 请求/响应拦截器用于 Token 注入和 401 自动刷新

## Linting 与格式化

| 工具 | 配置文件 | 用途 |
|------|----------|------|
| Ruff | `pyproject.toml`（`[tool.ruff]` 段） | Python 代码检查与格式化 |

Ruff 替代 flake8 + isort + black 组合，配置在 `pyproject.toml` 中。
