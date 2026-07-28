# 代码健壮性复查报告（2026-07-21）

## 检查范围

- 分支：`codex/2026-07-16-robustness-remediation`
- 提交：`fe39900`（相对 `main` 领先 10 个提交）
- 重点：鉴权与配置、验证码与注册、额度并发、面试会话并发、Outbox 补偿、异步任务生命周期

## 自动化验证

- `python -m pytest`：141 passed，78 deselected，1 warning
- `python -m ruff check src tests`：通过
- 说明：默认配置只运行 `unit` 标记；依赖数据库、RabbitMQ、Milvus、SMTP 的 integration/e2e/fault 测试未在本地执行。

## 发现的问题

### P1：JWT 与邮件配置绕过统一 Settings，`.env` 部署可能启动失败或使用错误配置

**位置**：`src/auth/jwt.py:11-30`、`src/utils/mail.py:5-9`、`src/config/settings.py:5-65`

`Settings` 使用 Pydantic 从 `.env` 读取配置，但 JWT 和邮件模块再次直接调用 `os.getenv()`。Pydantic 读取 `.env` 不会把值回写到进程环境，因此只在 `.env` 中配置、未由容器显式注入的场景会出现：

- 生产环境的 `settings` 校验通过后，`jwt.py` 仍可能读不到 `JWT_SECRET` 并在导入时抛错；
- 开发环境会生成一次性随机密钥，进程重启后现有 token 全部失效；多 worker 进程还会各自使用不同密钥；
- SMTP 配置同样可能被忽略。

**建议**：JWT、SMTP 等模块只从 `src.config.settings.settings` 取值；不要在业务模块中重复读取环境变量。增加一个使用临时 `.env`、不设置 `os.environ` 的启动回归测试。

### P1：注册流程不是事务，失败会消耗邮箱验证码并遗留半创建用户

**位置**：`src/auth/api.py:232-255`

注册流程先原子消耗邮箱验证码，再检查用户名/邮箱冲突，随后分别创建 `User` 和 `UserQuota`，整个过程不在同一数据库事务内。因此：

- 用户名或邮箱冲突时，合法验证码被永久消耗；
- 创建额度记录失败时，用户已经落库，重试会因用户重复而失败；
- 两个并发注册请求仍需依赖数据库唯一约束，其中一个失败会以未归一化的 500 返回。

**建议**：在同一事务中完成验证码条件更新、唯一性确认、用户与额度创建；捕获唯一约束冲突并返回 409。验证码只应随成功注册一同提交。

### P1：邮件发送吞掉全部故障，接口会在未发送邮件时返回成功

**位置**：`src/utils/mail.py:12-24`、`src/auth/api.py:209-225`

`send()` 在缺少账号配置时直接返回，在连接、认证或发送失败时吞掉所有异常；上层 `_send_email()` 无法判断结果，`/send-code` 始终返回“验证码已发送”。同时验证码记录在发送前写入数据库，失败请求仍占用一分钟/每日限额。

此外，同步 `smtplib` 调用直接运行在 async 路由中，SMTP 超时会阻塞事件循环；当前连接没有显式超时。

**建议**：让发送函数返回明确结果或抛出类型化异常；通过 `asyncio.to_thread`/任务队列执行并设置连接超时；发送失败时删除/失效本次 challenge，接口返回 503。不要记录或输出验证码明文。

### P1：Agent 额度在业务执行前扣减，失败请求不会退款

**位置**：`src/middleware/quota.py:21-45`

`POST /api/topic/generate` 在调用业务处理器之前扣除额度。后续如果发生参数错误、LLM/数据库/Milvus 故障、超时或服务返回 5xx，额度不会恢复，用户会为未完成的请求付费。

**建议**：把额度预留与最终结算建模为可恢复状态，成功后提交，失败时释放；至少应在 `call_next` 返回非成功状态或抛异常时原子退款，并用请求幂等键防止重试重复扣费。

### P2：后台任务缺少异常消费和应用关闭管理

**位置**：`src/api/interview_api.py:160-167`、`src/main.py:68-72`

面试事件任务的完成回调只从集合中移除任务，没有调用 `task.result()`，发布失败会产生 “Task exception was never retrieved”，且没有可靠重试。Outbox worker 由未保存引用的 `create_task()` 启动，关闭时没有设置 stop event、等待 worker 完成或显式取消。

**建议**：使用 FastAPI lifespan 管理 worker 句柄和 stop event；关闭时停止并 await。事件发布使用持久化 outbox，或至少在回调中消费并记录异常。

### P2：Outbox 成功状态更新不是原子操作

**位置**：`src/workers/outbox_worker.py:81-85`

Milvus 写入成功后，先将 Outbox 标记为 `PROCESSED`，再把 Topic 改为 `ACTIVE`。若第二次数据库更新失败，任务不会重试，Topic 会永久停留在 `MILVUS_FAILED`；反过来，Milvus 写入与数据库状态本身也不具备端到端原子性。

**建议**：至少把 Outbox 与 Topic 的两次 PostgreSQL 更新放在同一事务中，并检查条件更新的影响行数。Milvus 写入使用稳定主键/upsert，保证 lease 到期后的重复投递幂等。

## 已确认的改进

- 面试房间增加了用户所有权、过期时间与乐观版本控制。
- CAPTCHA/邮箱验证码改为哈希存储和条件更新消费。
- NL-to-SQL 增加 AST allowlist、只读连接、超时和结果条数限制。
- Outbox 增加 claim/lease、退避、重试上限和 dead-letter。
- Agent 写入失败不再被错误包装成成功。

## 建议处理顺序

1. 统一配置来源，修复 JWT/SMTP 读取。
2. 将注册和验证码消费纳入同一事务。
3. 修复邮件发送结果与额度结算语义。
4. 完善后台任务生命周期和 Outbox 成功提交事务。
5. 在 CI 中实际运行 integration、concurrency、fault 测试，并为上述失败路径补回归用例。
