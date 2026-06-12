# 错误处理

> **生成时间**：2026-06-12 00:06:53  
> **基于提交**：168f526（main）  
> **覆盖模块**：全部

---

## 错误体系

| 错误类型 | 基类 | 使用场景 |
|----------|------|----------|
| `SlavePermissionError` | `Exception` | Slave 尝试执行非白名单或 read 能力 |
| `AgentGuardError` | `Exception` | Agent 预算耗尽（迭代/时间/Token） |
| `CircuitBreakerError` | `Exception` | 熔断器开启时请求被拦截 |
| `ValueError` | 内置 | 输入验证失败（输入过短/过长/纯符号） |
| `RuntimeError` | 内置 | CapabilityRegistry 冻结后注册、重复题目保存 |
| 通用 `Exception` | 内置 | 网络超时、LLM API 错误、数据库连接异常 |

## 错误传播

```mermaid
graph TD
  A[LLM API 超时] --> B[LLMClient.ainvoke<br/>异常冒泡]
  B --> C[ToolExecutor.execute<br/>捕获 → ToolResult{success:false}]
  C --> D[MasterSession<br/>_parse_output 路由到 _handle_incomplete]
  D --> E[HTTP 200 + success:false 响应]
  
  G[DB 连接异常] --> H[FastAPI 全局异常处理]
  H --> I[HTTP 500 JSONResponse]
  
  J[输入验证失败] --> K[Pydantic field_validator]
  K --> L[HTTP 422 ValidationError]
```

## 错误分级

| 级别 | 场景 | 处理策略 |
|------|------|----------|
| **Fatal** | LLM API Key 无效、PG 连接拒绝、Milvus 不可达 | Agent 状态 → ERROR，返回 HTTP 500/502 |
| **Degraded** | 归一化 LLM 超时、Embedding 模型不可用 | 降级路径，继续执行（零向量/原文匹配） |
| **Recoverable** | Milvus 写入失败 | Outbox 补偿（PENDING → Worker 定时重试），不阻塞主流程 |
| **Ignorable** | LangFuse 追踪上报失败、PromptCallLog 写入失败 | 静默忽略（best-effort），不影响业务 |

## 降级路径

```
正常路径:          normalize → search → verify → {HIT|MISS} → generate → write

归一化降级:        [LLM 超时] → 原文作为 core_concept → search（降级但继续）

Embedding 降级:    [模型不可用] → encode() 返回零向量 → search 返回空 → MISS → generate

Milvus 降级:       [连接超时] → search 返回空 → MISS → generate（跳过召回直接生成）

写入降级:          [Milvus 写入失败] → Outbox PENDING → Worker 补偿重试
```

## Outbox 补偿机制

```
1. PG 事务中写入 Topic 主表 + 8 关联表
2. PG 事务中写入 Outbox 记录（status=PENDING）
3. 提交 PG 事务
4. 尝试同步写入 Milvus
   ├─ 成功 → Outbox.status = PROCESSED
   └─ 失败 → Outbox 保持 PENDING（compensable=true）
5. 后台 Worker 每 30s 轮询 PENDING 记录
   ├─ retry_count < 3 → 重试 Milvus 插入
   └─ retry_count ≥ 3 → Outbox.status = FAILED（告警）
```

## 日志策略

| 日志级别 | 使用场景 | 输出目标 |
|----------|----------|----------|
| DEBUG | 未使用 | — |
| INFO | 未显式使用（依赖框架默认日志） | stdout/stderr |
| WARN | 优雅降级事件（Embedding 不可用、Milvus 不可达） | stderr（`logging.warning`） |
| ERROR | 关键操作失败（LLM 调用失败、DB 写入失败） | stderr + `AgentTrace.errors` |

## 告警与监控

当前监控基础设施状态：

- **LangFuse**：LLM 调用链路追踪（需配置 `LANGFUSE_PUBLIC_KEY` 等环境变量）
- **OpenTelemetry**：框架已集成但仍处于预留状态（`src/tracing/__init__.py` 为空）
- **告警规则**：[待补充：当前代码中未发现显式的告警规则配置]
- **健康检查**：`GET /ping` 返回服务状态，可用于负载均衡健康探测
