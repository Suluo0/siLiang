# siLiang 健壮性处理计划

更新时间：2026-07-11

## 1. 审查范围与基线

本计划承接 2026-07-10 未完成的健壮性审查，覆盖安全与 API、并发与数据一致性、测试、CI 和部署。

当前验证基线：

- 分支：`main`
- 默认测试：收集 168 项，排除 9 项，实际运行 159 项
- 结果：99 passed、51 errors、9 xfailed、9 deselected
- 51 个 error 均在 `tests/conftest.py` 建库阶段因 PostgreSQL 连接被拒绝产生，不能视为 51 个产品缺陷；这也说明默认测试命令没有自动准备依赖或快速失败
- pytest 报告 `collect_ignore_glob` 为未知配置项

## 2. 风险清单与优先级

### P0：发布前必须处理

1. **限制 NL-to-SQL 的数据库权限和语法面**
   - 位置：`src/agentv3/capabilities/query_db.py`
   - 现状：LLM 生成的 SQL 经正则黑名单检查后，直接通过应用默认连接执行；正则校验不能完整覆盖 PostgreSQL 的只读绕过、资源消耗、敏感表读取和函数副作用。
   - 处理：使用独立只读数据库角色；只授权允许的 schema/table/column；事务设置 `READ ONLY`、`statement_timeout`、`lock_timeout`；改用 SQL AST 解析和 allowlist；禁止系统目录、危险函数、CTE 内写操作和任意函数调用；响应中不回传原始数据库错误。
   - 验收：针对多语句、注释混淆、CTE、系统表、`pg_sleep`、大笛卡尔积、函数副作用的攻击测试全部拒绝；数据库角色无法执行 DDL/DML。

2. **修正 outbox 的并发消费和失败回滚策略**
   - 位置：`src/workers/outbox_worker.py`
   - 现状：轮询全部 `PENDING` 记录，没有 claim/lease 或 `FOR UPDATE SKIP LOCKED`；多实例可重复处理。重试耗尽后物理删除 Topic 及关联业务数据，外部系统暂时故障可能造成不可逆数据丢失。
   - 处理：增加原子 claim、租约、幂等键和指数退避；将失败记录转入 dead-letter 状态；Topic 标记失败并保留数据；人工或自动补偿成功后再激活；告警失败必须可观测。
   - 验收：两个 worker 并发时同一事件只产生一次外部副作用；进程在任意步骤崩溃后可恢复；重试耗尽不删除业务数据。

3. **统一鉴权语义，默认拒绝**
   - 位置：`src/middleware/auth.py`、`src/auth/deps.py`
   - 现状：未带 token 时中间件放行并标记“配额耗尽”，带无效 token 时返回 401；路由依赖又实施另一套鉴权。公开路径通过精确字符串维护，容易出现新路由漏保护和行为不一致。
   - 处理：明确匿名可访问的路由并在路由层声明；其余路由统一 401；删除重复鉴权路径或让中间件只负责解析身份；对 token `sub`、`ver` 类型和值进行严格校验；缓存失效与用户禁用/改密保持一致。
   - 验收：为全部路由生成鉴权矩阵；无 token、畸形 token、过期 token、禁用用户、改密后旧 token 的结果一致且有测试覆盖。

4. **补齐生产密钥与配置启动校验**
   - 位置：`src/config/settings.py`、`.env.production`、compose/entrypoint
   - 处理：生产环境禁止空值和示例密钥；JWT、数据库、SMTP、LLM、消息队列密钥只从 secret provider/环境注入；启动时校验长度、默认值和环境组合；日志中统一脱敏。
   - 验收：缺少或使用默认密钥时生产启动失败；仓库及构建产物 secret scan 无有效凭据。

### P1：高优先级健壮性

5. **消除异步请求路径中的同步阻塞 I/O**
   - 位置：`src/auth/hash.py`、`src/utils/mail.py`、`src/tools/embedding.py`、`src/workers/outbox_worker.py`
   - 现状：bcrypt、`smtplib`、同步 `httpx.post`、Milvus 同步调用可能阻塞事件循环；SMTP 异常被静默吞掉。
   - 处理：bcrypt 放入受限线程池；邮件改为队列任务或异步客户端；embedding 使用复用连接池的 `httpx.AsyncClient`；为外部调用配置连接/读取/总超时、有限重试、熔断和指标。
   - 验收：外部服务超时期间健康检查和普通请求仍可响应；负载测试中事件循环延迟在约定阈值内。

6. **验证码和邮件验证码改为原子消费**
   - 位置：认证 API、`src/models/captcha.py` 及验证码相关模型
   - 处理：验证码只存哈希；校验与 `used=true` 在同一条件更新中完成；增加尝试次数、发送频率、IP/账号限流和过期清理；防止并发重复使用和账号枚举。
   - 验收：并发提交同一验证码只有一个成功；暴力尝试和高频发送触发限流；响应不泄露账号是否存在。

7. **收紧异常处理和可观测性**
   - 现状：多处 `except Exception` 返回空结果或直接 `pass`，会把依赖故障伪装成“无数据/成功”。部分 API 将 `str(e)` 回传给客户端。
   - 处理：捕获具体异常；对外返回稳定错误码和 correlation id；内部记录结构化日志及堆栈；为 LLM、Milvus、RabbitMQ、PostgreSQL、SMTP 建立成功率/延迟/重试/dead-letter 指标。
   - 验收：故障注入时客户端不看到内部堆栈、SQL 或密钥；监控能区分无数据、超时、格式错误和依赖不可用。

8. **约束 LLM 输出解析与资源使用**
   - 位置：`src/agentv3/**`
   - 处理：所有 LLM 输出通过 Pydantic/schema 校验；限制字符串、数组、嵌套深度和总响应大小；JSON 解析失败采用有限重试；对 prompt/context 做长度限制；对外部调用统一预算和取消传播。
   - 验收：畸形 JSON、超大数组、错误类型、超时和取消都有确定结果，不产生半写入状态。

### P2：测试、CI 与部署

9. **使默认测试可重复、可快速失败**
   - 位置：`tests/conftest.py`、`pyproject.toml`
   - 处理：单元测试默认不依赖 PostgreSQL；集成测试通过 compose/testcontainers 自动准备数据库，或在依赖缺失时明确 skip；会话级探活只执行一次；移除无效的 `collect_ignore_glob` 配置；为测试数据库增加安全护栏，拒绝连接非测试库。
   - 验收：全新机器一条文档化命令可运行；数据库未启动时 5 秒内给出单一明确错误或 skip，而不是每个测试等待超时。

10. **建立 CI 质量门禁**
    - 处理：固定 Python 3.12（与 `pyproject.toml` 一致）；依赖使用 lock/hash 固定，避免全部使用无上限的 `>=`；CI 分为 lint、unit、integration、security、image build；启用 Ruff、类型检查、依赖漏洞和 secret 扫描；上传覆盖率和测试报告。
    - 验收：PR 必须通过所有门禁；unit 与 integration 结果分开可见；依赖更新由自动 PR 管理。

11. **强化容器运行时**
    - 位置：`Dockerfile`、compose、entrypoint
    - 处理：Python 版本与项目声明一致；镜像按 digest 固定；只读根文件系统、drop capabilities、资源限制、日志轮转；迁移使用单独 job/leader，避免多副本同时迁移；健康检查区分 liveness/readiness。
    - 验收：多副本启动不会并发迁移；数据库或 Milvus 不可用时 readiness 失败但进程行为可控；镜像扫描无高危漏洞。

## 3. 实施顺序

### 阶段 A：建立可信基线（0.5～1 天）

- 修复 pytest 配置，拆分 unit/integration 标记。
- 自动准备测试 PostgreSQL，并记录当前覆盖率。
- 建立最小 CI：lint + unit + integration。

完成定义：本地和 CI 的结果一致，失败可复现。

### 阶段 B：封堵 P0（2～4 天）

- 独立只读 SQL 角色、AST allowlist、查询超时与结果限制。
- outbox claim/lease、幂等、dead-letter，取消物理删除回滚。
- 统一鉴权策略与配置/密钥启动校验。
- 为每项缺陷先写回归测试，再修改实现。

完成定义：P0 验收用例全部通过，故障注入不造成越权或数据丢失。

### 阶段 C：外部依赖和并发治理（2～3 天）

- 将同步阻塞操作移出事件循环。
- 验证码原子消费与限流。
- 统一 timeout/retry/backoff/circuit-breaker，加入结构化日志和指标。

完成定义：依赖超时和多实例并发测试通过，无重复副作用。

### 阶段 D：交付加固（1～2 天）

- 固定依赖和基础镜像，完善安全扫描。
- 分离迁移任务，配置非 root、只读文件系统和资源限制。
- 运行完整 unit/integration/e2e、并发和故障注入测试。

完成定义：发布检查表签署，保留测试、扫描和演练证据。

## 4. 建议新增的关键测试

- `test_query_db_security.py`：SQL 绕过、系统表、危险函数、超时、超大结果。
- `test_outbox_concurrency.py`：双 worker、重复事件、崩溃恢复、租约过期、dead-letter 重放。
- `test_auth_matrix.py`：所有路由与所有身份状态的矩阵测试。
- `test_captcha_race.py`：并发消费、过期、尝试次数、发送限流。
- `test_dependency_failures.py`：PostgreSQL、Milvus、RabbitMQ、LLM、SMTP 的超时与恢复。
- `test_config_validation.py`：生产默认密钥、空密钥、非法 URL、错误环境组合。

## 5. 完成判定

只有同时满足以下条件，健壮性整改才算完成：

- P0/P1 项均有对应回归测试并通过。
- unit、integration、e2e 三层测试有明确命令和环境说明。
- 不存在因外部依赖短暂故障导致的业务数据物理删除。
- 所有 LLM/数据库边界均为 allowlist + 最小权限 + 超时。
- 生产配置无默认密钥，日志和 API 响应不泄露内部错误。
- 多实例并发与故障恢复演练通过，证据由 CI 保存。
