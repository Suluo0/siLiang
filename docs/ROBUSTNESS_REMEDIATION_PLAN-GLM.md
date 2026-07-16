# siLiang 健壮性审查报告（GLM）

> 审查对象：`C:\workIn\siLiang`（TopicSystem v3 —— 基于 LangGraph Agent 的面试题生成系统）
> 技术栈：FastAPI + Tortoise ORM + PostgreSQL + Milvus + RabbitMQ + DeepSeek LLM + Vue3 前端
> 审查日期：2026-07-11
> 审查方式：全量代码静态审查（6 个模块并行审查 + 核心文件交叉验证），独立于既有 `ROBUSTNESS_REMEDIATION_PLAN.md` 重新开展
> 等级定义：**P0** 发布前必修（安全漏洞 / 数据丢失 / 越权 / 数据完整性）｜**P1** 高（影响可用性或正确性）｜**P2** 中｜**P3** 低/提示

---

## 0. 总体结论

系统架构方向正确（Capability 自举注册、Master/Slave 读写隔离、ToolExecutor 统一切面、Outbox 补偿模式、CircuitBreaker/TokenBudget 多层防护），但**防御层多处未实际接线，当前不具备生产级健壮性**。最严重的是存在一组相互叠加的缺陷，使得**认证、验证码、配额三条防线在当前实现下均已被实质性绕过**：

- 验证码答案明文返回客户端 → 防自动化机制失效
- 鉴权中间件对无 token 请求默认放行 + 面试 API 完全无鉴权 + IDOR
- **中间件注册顺序错误 → 配额系统对所有用户（含已登录）完全失效**
- Access token 有效期 7 天且中间件不校验 token 类型 → token 分层防护失效
- NL-to-SQL 用应用主连接 + 正则黑名单执行 LLM 生成的 SQL → SQL 注入/DoS/系统表泄露
- Outbox 重试耗尽物理删除业务数据 + Milvus 静默降级被误标 PROCESSED → 不可逆数据丢失
- 数据库凭据硬编码提交至 Git

发布前必须修复全部 P0 项（共 14 项），首个迭代内修复 P1 项。

**统计**：P0 ×14 ｜ P1 ×24 ｜ P2 ×17 ｜ P3 ×12

---

## 1. P0 —— 发布前必修

### P0-1 ｜ NL-to-SQL 用应用主连接执行 LLM 生成 SQL，注入面/DoS/系统表泄露

- **位置**：`src/agentv3/capabilities/query_db.py:14-20`（FORBIDDEN_KEYWORDS）、`:61-76`（validate_sql）、`:123-144`（执行）
- **涉及范围**：`query_database` 能力，所有自然语言查库路径
- **问题描述**：LLM 生成的 SQL 仅经正则关键字黑名单校验后，**用应用默认数据库连接（具备完整 DDL/DML 权限）直接执行**。黑名单只拦 DML/DDL 关键字，无法覆盖：
  1. **危险函数**：`pg_sleep(29)` 在 ToolExecutor 30s 超时内合法通过，占用连接 29 秒（DoS）；`pg_read_file`/`pg_ls_dir`/`lo_import` 在 superuser 权限下可读文件系统。
  2. **系统目录表**：`SELECT usename, usesuper FROM pg_catalog.pg_user` 泄露数据库用户列表与 superuser 标记；`information_schema.tables` 泄露全部表结构。
  3. **递归 CTE 资源耗尽**：`WITH RECURSIVE t AS (... SELECT n+1 FROM t WHERE n<1000000000) SELECT * FROM t` 造成 CPU/内存耗尽。
  4. **执行失败时 `str(e)` 原始数据库错误回传客户端**（line 140-144），泄露真实表名/列名/schema 细节。
- **失败场景**：LLM 被 prompt 注入诱导生成 `SELECT pg_sleep(29); SELECT usename FROM pg_catalog.pg_user` → `validate_sql` 通过（pg_sleep/pg_user 不在禁止列表）→ 执行成功，泄露用户信息 + 占用连接。
- **修改建议**：
  1. 使用独立**只读数据库角色**（`topic_readonly`），仅授权允许的 schema/table/column；事务设 `READ ONLY`、`statement_timeout`、`lock_timeout`。
  2. 改用 **SQL AST 解析 + allowlist**（如 `sqlglot`），禁止系统目录（`pg_catalog.`/`information_schema.`/`pg_` 前缀）、危险函数、`WITH RECURSIVE`、CTE 内写操作、任意函数调用。
  3. 响应中不回传原始数据库错误，仅返回稳定错误码。
  4. 结果集强制行数上限。

### P0-2 ｜ 验证码答案明文返回客户端，防自动化机制完全失效

- **位置**：`src/auth/api.py:143-147`；前端 `TOPICSYSTEM_Web/src/views/Auth/Login.vue:97-103,19,40`
- **涉及范围**：登录、注册、发送邮箱验证码 —— 所有依赖 CAPTCHA 的端点
- **问题描述**：`get_captcha` 将验证码明文随响应返回：`return {"captcha_id": ..., "captcha_text": code}`。前端直接 `{{ captchaText }}` 显示。任何脚本只需 GET `/api/auth/captcha` 读取 `captcha_text` 即可自动填答案。验证码仅 4 位数字（10000 种组合）。
- **失败场景**：脚本调 `/captcha` 拿 captcha_id + captcha_text → 调 `/login` 传答案 → 绕过验证码暴力破解或撞库，每秒数十次。
- **修改建议**：响应不返回 `captcha_text`，改为返回图片（base64 PNG/SVG）；前端用 `<img>` 展示。生产环境强制关闭明文返回。

### P0-3 ｜ 邮箱验证码未绑定邮箱地址，邮箱验证完全无意义

- **位置**：`src/auth/api.py:180`（存储，不记录目标邮箱）、`:196`（校验，`Captcha.filter(code=req.email_code, used=False)` 不校验邮箱）
- **涉及范围**：注册流程的邮箱所有权验证
- **问题描述**：`send_verification_code` 将 6 位验证码存入通用 Captcha 表但不记录目标邮箱；注册时按 `code` 值查找不校验邮箱归属。攻击者可向自己邮箱发码，用该码注册绑定**他人邮箱**的账号。
- **失败场景**：攻击者 `/send-code` 到自己邮箱获 code=123456 → 用该码注册 `victim@company.com` → 验证通过，攻击者拥有绑定他人邮箱的账号。
- **修改建议**：Captcha 表增加 `target_email` 字段，校验时同时匹配 `code` 与 `email`。

### P0-4 ｜ 中间件注册顺序错误，配额系统对所有用户完全失效

- **位置**：`src/main.py:30-31`
- **涉及范围**：所有需要配额控制的端点（`/api/topic/generate`、`/api/topic/{id}` 等）
- **问题描述**：`app.middleware("http")(auth_middleware)` 先注册、`app.middleware("http")(quota_middleware)` 后注册。Starlette `add_middleware` 做 `insert(0,...)`，构建栈时 `reversed`，**后注册的 quota_middleware 成为外层先执行**。`quota_middleware` 第一步 `getattr(request.state, "user_id", None)`，但 `user_id` 由 `auth_middleware` 设置（auth.py:50），此时尚未执行 → **uid 恒为 None → quota_middleware 直接 return → 配额从不扣减**。已登录用户访问 `/generate` 的 agent_credits、访问详情的 topic_credits 均永不减少。
- **失败场景**：任意已登录用户无限次调用 `/api/topic/generate`，agent_credits 永不耗尽；无限次浏览题目详情，topic_credits 永不减少。
- **修改建议**：对调注册顺序（让 auth 后注册成外层先执行）；或将配额逻辑并入 auth_middleware 内部消除顺序依赖。更稳妥的做法是路由层显式 `Depends` 鉴权+配额。

### P0-5 ｜ 鉴权中间件对无 token 请求默认放行，匿名用户可无限制调用 LLM

- **位置**：`src/middleware/auth.py:18-21`；`src/middleware/quota.py:10-12`
- **涉及范围**：所有非 PUBLIC_PATHS 端点（含 `/api/topic/generate`、整个面试 API）
- **问题描述**：无 Bearer token 时中间件不拒绝，仅设 `request.state.quota_exhausted=True` 后放行；配额中间件见 `uid is None` 直接跳过；`/generate` 路由不检查 `quota_exhausted`。匿名用户可无限次调用 DeepSeek LLM，造成经济损失与 DoS。
- **失败场景**：攻击者循环 POST `/api/topic/generate`，每次消耗一次 LLM 调用，无任何限制。
- **修改建议**：非 PUBLIC_PATHS 无 token 直接 401（默认拒绝）；`quota_exhausted` 降级逻辑仅限特定匿名可访问端点。

### P0-6 ｜ 面试 API 完全无鉴权，且存在 IDOR（越权访问他人面试会话）

- **位置**：`src/api/interview_api.py:70-71`（start）、`122-124`（answer）、`160-162`（summary）
- **涉及范围**：整个面试模块（简历/JD 分析、面试回答、面试总结）
- **问题描述**：三个端点均不检查 `request.state.user_id`：`/start` 接受 `request` 但从未使用；`/answer` 通过 `room_id` 从内存 `_sessions` 取会话不校验调用者身份；`/{room_id}/summary` 不接收 `request`，任何知道 room_id 的人可读取他人简历分析、JD 分析、全部回答。
- **失败场景**：用户 A 启动面试获 `room_id=R`，用户 B 调 `GET /api/interview/R/summary` 读取 A 的简历分析与面试回答 —— 泄露敏感个人信息；B 还可 `POST /api/interview/answer` 向 A 的会话注入回答篡改数据。
- **修改建议**：`/start` 提取 `request.state.user_id` 绑定到会话；`/answer`、`/summary` 校验 `request.state.user_id == session.owner_id`。

### P0-7 ｜ Access token 有效期 7 天，与 refresh token 相同，token 分层防护失效

- **位置**：`src/auth/jwt.py:19-20`（`ACCESS_EXPIRE_MINUTES=10080` 即 7 天，注释却写 "15min"）
- **涉及范围**：所有受保护端点的 token 安全性
- **问题描述**：access token 与 refresh token 均 7 天过期。access token 暴露面大（前端 localStorage），设计上应短命（15-30 分钟）。当前实现使被盗 access token 可用长达 7 天，refresh token 机制失去意义。`expires_in` 返回前端 604800 秒。
- **修改建议**：`ACCESS_EXPIRE_MINUTES=15`（至多 30），保持 `REFRESH_EXPIRE_DAYS=7`，同步更新 `expires_in`。

### P0-8 ｜ 中间件不校验 token 类型，refresh token 可当 access token 使用

- **位置**：`src/middleware/auth.py:28-32`；`src/auth/deps.py:37-39`
- **涉及范围**：所有受中间件保护的路由
- **问题描述**：`auth_middleware` 调 `decode_token` 后直接取 `payload["sub"]`，不检查 `payload.get("type")=="access"`；`decode_token` 也不校验类型。refresh token（type=refresh）可被当作 access token 访问所有端点（`/auth/me`、`/topic/generate`、`/auth/change-password` 等）。
- **修改建议**：`decode_token` 后增加 `if payload.get("type") != "access": return 401`。

### P0-9 ｜ JWT_SECRET 未配置时静默用随机密钥，多 worker 部署鉴权崩溃

- **位置**：`src/auth/jwt.py:10-16`；`src/config/settings.py`（未定义 JWT_SECRET 字段）
- **涉及范围**：全局身份认证
- **问题描述**：`JWT_SECRET` 未设置则每次启动生成随机密钥并 `warnings.warn`。多 worker（`entrypoint.sh` 默认 `UVICORN_WORKERS=2`）各 worker 密钥不同 → token 在 worker 间不可验证 → 用户时而 401 时而正常，极难排查。重启后所有已签发 token 失效。
- **修改建议**：settings.py 定义 `JWT_SECRET: str`（必填），startup 校验非空且非示例值，否则 `raise RuntimeError` 拒绝启动。

### P0-10 ｜ 数据库凭据硬编码并提交至 Git 仓库

- **位置**：`docker-compose.yml:92`；`scripts/init_db_roles.sql:8,11,14`；`.env.production:6,9`
- **涉及范围**：全部环境的 PostgreSQL 访问
- **问题描述**：`docker-compose.yml:92` 硬编码 `DATABASE_URL="postgres://topic_app:Top1cApp%232026@postgres:5432/topic"`；`init_db_roles.sql` 明文写入三个角色密码 `Top1cAdm1n#2026`/`Top1cApp#2026`/`Top1cRead#2026`；`.env.production` 带默认占位密钥 `change-me-...`。这些文件均被 git 跟踪。任何能访问仓库者即可获取数据库完整凭据，Git 历史永久留存。
- **失败场景**：攻击者获取仓库访问权 → 用 `Top1cApp#2026` 连接生产 PostgreSQL → 读取/篡改/删除全部面试题数据。
- **修改建议**：所有密码改为环境变量注入（`${DB_APP_PASSWORD}`）；SQL 用 envsubst 在启动时注入；立即轮换全部密码并用 `git filter-repo` 清除历史；`.env.production` 改名 `.env.production.example` 并加入 `.gitignore`。

### P0-11 ｜ Outbox 重试耗尽物理删除全部业务数据（不可逆）

- **位置**：`src/workers/outbox_worker.py:82-87,105-110`（`_rollback_topic`）；`:31`（MAX_RETRIES=3）、`:32`（POLL_INTERVAL=30）
- **涉及范围**：所有 Outbox 补偿失败的 Topic 及其 11 张关联表
- **问题描述**：重试达 `MAX_RETRIES=3` 后，`_rollback_topic` 在事务中**硬删除** Topic 及全部关联模型（prerequisite/core_concept/derivative/extension/evaluation_anchor/similar_question/advanced_question/reference/review_log/user_topic_progress/user_topic_status）再删除 Topic。重试无指数退避，3 次重试间隔仅 30 秒 → **约 90 秒内 Milvus 持续故障即触发删除**。
- **失败场景**：Milvus 因 OOM 重启需 2 分钟恢复 → worker 在 90 秒内完成 3 次重试全失败 → 物理删除 Topic 及全部关联数据 → Milvus 恢复后数据已永久丢失，LLM 生成的原始内容已删除无法重建。
- **修改建议**：物理删除改软删除（`status="MILVUS_FAILED"`）保留数据；增加指数退避（30s→120s→600s）；`MAX_RETRIES` 提高或改基于时间策略；回滚前二次告警。

### P0-12 ｜ Outbox：Milvus/Embedding 静默失败被误标 PROCESSED，破坏最终一致性

- **位置**：`src/workers/outbox_worker.py:62-76`；`src/tools/milvus_client.py:103-110`（insert 在不可用时静默 return）；`src/tools/embedding.py:45-74`（失败返回零向量）
- **涉及范围**：所有 Outbox 补偿流程，PG 与 Milvus 数据一致性
- **问题描述**：`_process_one` 成功路径依赖两个静默降级调用：① `encoder.encode()` 在 API key 缺失/HTTP 非 200/异常时返回**零向量**不抛异常；② `milvus.insert()` 在 `_check_available()` 返回 False 时直接 `return` 不抛异常。随后 worker 将 record 标 `PROCESSED`、Topic 标 `ACTIVE`。
- **失败场景**：Milvus 短暂不可用 → `insert` 静默返回 → record 标 PROCESSED、Topic 标 ACTIVE → PG 显示已上线但 Milvus 无向量，语义搜索永远搜不到该题。或 Embedding API 不可用 → 插入零向量 → 搜索匹配度恒为 0。两种情况都不触发重试或告警。
- **修改建议**：`insert()` 不可用时抛 `MilvusUnavailableError`；`encode()` 失败抛异常或返回 sentinel；`_process_one` 在 insert 后验证写入结果。

### P0-13 ｜ Master 在 Slave 写入失败时仍返回 success=True

- **位置**：`src/agentv3/master.py:192-220`（`_handle_generated`）
- **涉及范围**：所有生成新题目的请求
- **问题描述**：`_handle_generated` 中：① Slave.execute() 抛异常时 `except Exception: pass`（line 212-213）后落入 line 215 返回 `{"success": True, "source": "generated"}` 但无 `topic_id`；② Slave 返回 `SlaveResult(success=False)` 时 `sr.topic_id` 为 None，`if sr.topic_id:` 不满足，同样返回 success=True；③ Slave 部分成功时 `compensable`/`partial`/`failed` 信息被完全丢弃。
- **失败场景**：用户请求生成"Redis 持久化" → LLM 生成成功 → Slave 写 PG 唯一约束冲突返回 success=False → Master 返回 `{"success": True}` 但无 topic_id → 调用方认为成功，实际数据未写入。
- **修改建议**：`except: pass` 改为记录日志并设错误状态；检查 `sr.success`/`sr.partial`，topic_id 为 None 或 success=False 时返回 `success: False`；传播 `compensable`/`failed` 供调用方决策。

### P0-14 ｜ 前端 v-html 渲染未转义的后端内容，存储型 XSS

- **位置**：`TOPICSYSTEM_Web/src/views/Topic/topic_detail.vue:33,39,45,68,84,92`；`formatText`（line 244-247）
- **涉及范围**：面试题详情页所有文本字段（one_liner/core_summary/core_points/detailed_explanation/traps/bonuses）
- **问题描述**：6 处 `v-html="formatText(...)"`，`formatText` 仅 `text.replace(/\n/g,'<br>')` **完全不过滤 HTML 标签**。后端返回字段含 `<img src=x onerror=alert(document.cookie)>` 将被浏览器执行。这些字段可由用户输入触发 AI 生成（Chat 页 `/api/topic/generate`）。结合 token 存 localStorage（request.js:11），XSS 可直接窃取 JWT 实现 account takeover。
- **修改建议**：`formatText` 先 HTML 转义再替换换行；或引入 DOMPurify；或改用 `{{ }}` 插值 + CSS `white-space: pre-wrap`。

---

## 2. P1 —— 高优先级（影响可用性或正确性）

### P1-1 ｜ 用户缓存致改密/禁用后旧 token 仍有 60 秒窗口期

- **位置**：`src/middleware/auth.py:38-40,44-48`
- **涉及范围**：密码修改、账号禁用后的 token 失效语义
- **问题描述**：中间件将用户信息（含 `token_version`、`is_active`）缓存 60 秒。缓存命中时只比对缓存中的 `token_version` 与 token 的 `ver`，不查库。改密后 `token_version` 已 +1 但缓存仍是旧值，**60 秒内旧 token 仍可通过**；禁用账号同理。
- **失败场景**：用户发现异常后改密，攻击者持有的旧 access token 在 60 秒内仍可正常访问 API。
- **修改建议**：改密/禁用时主动清缓存 `user_cache.set(f"user_{uid}", None, ttl=0)`；或 TTL 降至 5-10 秒；或缓存只存非敏感字段，`token_version`/`is_active` 每次查库。

### P1-2 ｜ 验证码消费存在 TOCTOU 竞态，同一验证码可被并发复用

- **位置**：`src/auth/api.py:117-129`（`_verify_captcha`）
- **涉及范围**：登录、注册、发邮箱码的 CAPTCHA 校验
- **问题描述**：先读记录检查 `c.used`，再设 `c.used=True` 并 `save()`，是经典 read-then-write 竞态。两个并发请求同时读到 `used=False`，都通过检查，都标记已用，验证码被消费两次。
- **失败场景**：攻击者获取一个 captcha_id+答案后并发 10 个登录请求尝试不同密码，全部通过验证码检查，放大暴力破解效率。
- **修改建议**：原子更新 `updated = await Captcha.filter(id=captcha_id, used=False).update(used=True)`，`updated==0` 则拒绝。

### P1-3 ｜ 配额扣减 read-modify-write 竞态（中间件顺序修复后仍存在）

- **位置**：`src/middleware/quota.py:23-27,33-35`
- **涉及范围**：agent_credits 与 topic_credits 扣减
- **问题描述**：`quota.agent_credits -= 1; await quota.save()` 非原子。两个并发请求同时读到 `agent_credits=1`，都通过检查，都减为 0 保存 —— 实际两次操作都成功，多扣一次免费额度。`save()` 全字段覆盖还会覆盖并发修改。
- **失败场景**：用户并发 10 个 `/generate`，配额仅扣 1 次但执行 10 次 LLM 调用。
- **修改建议**：`updated = await UserQuota.filter(user_id=uid, agent_credits__gt=0).update(agent_credits=F("agent_credits")-1)`，`updated==0` 则 403。

### P1-4 ｜ 异步路径中同步阻塞 I/O（bcrypt / SMTP / embedding / milvus）

- **位置**：`src/auth/hash.py:7-12`（bcrypt）；`src/utils/mail.py:12-24`（smtplib）；`src/tools/embedding.py:50-62`（同步 httpx.post）；`src/tools/milvus_client.py:40,64,109` 等（同步 pymilvus）；`src/agentv3/capabilities/mastery_check.py:50-90`（CPU 密集 LCS/编辑距离）
- **涉及范围**：登录/注册/改密、发邮箱码、所有 embedding/milvus 调用、面试评分
- **问题描述**：bcrypt（100-300ms CPU 密集）、`smtplib.SMTP_SSL`（2-5s 无超时）、同步 `httpx.post`（timeout=30s）、pymilvus `Collection.load()`/`search()`/`insert()`（可阻塞数秒~数十秒）、mastery_check 的 LCS/编辑距离 O(m·n) 均在 `async def` 中直接调用，**阻塞整个事件循环**，期间所有其他请求（含健康检查）停滞。
- **失败场景**：SMTP 慢 → 一个 `/send-code` 阻塞事件循环 5 秒 → 全部请求排队；Milvus load 耗时 3s → 所有请求卡住。
- **修改建议**：bcrypt 放 `asyncio.to_thread`；SMTP 改 `aiosmtplib` 或 `to_thread` 并设超时；embedding 改 `httpx.AsyncClient`；milvus 同步调用包 `to_thread` 或迁 async client；mastery_check CPU 计算放线程池。

### P1-5 ｜ Embedding 失败静默返回零向量，污染 Milvus 数据与去重

- **位置**：`src/tools/embedding.py:64,74`；调用方 `write.py:253-259`、`duplicate.py:28-29`、`outbox_worker.py:64`
- **涉及范围**：Milvus 写入、去重检查、掌握度评分
- **问题描述**：HTTP 非 200 或异常返回 `np.zeros(1024)`，调用方无法区分"成功编码"与"失败"。零向量写入 HNSW 索引后该 topic 永不被语义检索命中（数据丢失无告警）；零向量做去重搜索必返回空，去重失效，重复题目被创建。
- **失败场景**：Embedding API 返回 429 → encode 返回零向量 → 写入 Milvus → 题目永久不可搜，后续相同概念去重全失效。
- **修改建议**：失败抛异常或返回 None；`save_to_milvus` 中 embedding 失败走 outbox 补偿而非写零向量。

### P1-6 ｜ LLM 客户端每次调用新建 httpx.AsyncClient 且从不关闭，连接池泄漏 + 无超时 + 禁用重试

- **位置**：`src/tools/llm_client.py:33-34,58,74,92`；`src/agentv3/master.py:114-121`
- **涉及范围**：所有 LLM 调用
- **问题描述**：① 每次调用 `_new_async_client()` 创建新 `httpx.AsyncClient` 传 `ChatOpenAI` 但从不 `aclose()`，高并发下连接池累积致 FD/端口耗尽；② 未传 `request_timeout`，DeepSeek 挂起时 `ainvoke` 无限阻塞，协程永久泄漏；③ `httpx.AsyncHTTPTransport(retries=0)` 显式禁用传输层重试，而 `LLMConfig` 定义的 `max_retries=2~3` 从未使用，瞬时错误直接失败。
- **失败场景**：连续 100 次 Agent 对话 → 100+ AsyncClient → 端口耗尽；DeepSeek 网络挂起 → ainvoke 永久阻塞 → 协程泄漏。
- **修改建议**：LLMClient 初始化时创建共享 AsyncClient 复用并 `aclose`；从 `LLMConfig` 读 timeout 传 `request_timeout`；用 `max_retries` 设 transport retries 或应用层退避重试。

### P1-7 ｜ `_clean_proxy_env()` 每次调用全局修改 os.environ，破坏其他 HTTP 客户端

- **位置**：`src/tools/llm_client.py:13-15,54,70,88`；`src/agentv3/master.py:114`
- **涉及范围**：所有 LLM 异步调用，及进程内所有依赖代理的 HTTP 客户端（embedding、langfuse tracing 等）
- **问题描述**：每次 `ainvoke`/`astream`/`ainvoke_structured` 删除进程级 `http_proxy`/`https_proxy` 等环境变量，是全局副作用。多协程交错时一个协程删代理变量会导致另一协程请求绕过代理。`httpx.AsyncClient(trust_env=False)` 已阻止 httpx 读环境代理，该函数多余且有害。
- **修改建议**：直接删除 `_clean_proxy_env()`，靠 `trust_env=False` 即可。

### P1-8 ｜ Milvus 连接状态永久缓存，网络断开后无重连，所有操作静默失败

- **位置**：`src/tools/milvus_client.py:47-51`
- **涉及范围**：所有 Milvus 操作
- **问题描述**：`_check_available()` 一旦 `_available=True`（首次连接成功后）后续永远返回 True 不再检查连接存活。Milvus 重启/网络中断后仍返回 True，所有操作进 try/except 被吞（返回 `[]` 或 `pass`），表现为"搜索全返回空、写入全静默丢弃"但 `available` 仍为 True，监控无法发现。
- **失败场景**：Milvus 重启 → 所有 search 返回 `[]` → 去重永远"无重复" → 大量重复题目创建 → 数据损坏无告警。
- **修改建议**：except 块中重置 `self._available=None` 触发重连；或每次操作前 ping；关键写操作失败应抛出。

### P1-9 ｜ search_sparse 直接拼接关键词到 Milvus 过滤表达式，表达式注入

- **位置**：`src/tools/milvus_client.py:94`
- **涉及范围**：知识库 sparse 检索（search_knowledge capability）
- **问题描述**：`expr_parts = [f'keywords like "%{kw}%"' for kw in keywords]` 直接插 `kw`。`kw` 含双引号可破坏表达式或注入额外条件，如 `kw='a" or 1==1 or topic_id like "b'` 使表达式返回全部记录。keywords 来源可追溯到用户输入或 LLM 生成，不可信。
- **修改建议**：对 `kw` 转义 `"` 和 `\`，或参数化查询。

### P1-10 ｜ Topic.topic 无唯一约束，save_to_postgres 存在 TOCTOU 竞态

- **位置**：`src/models/topic.py:11`；`src/agentv3/capabilities/write.py:216-218`
- **涉及范围**：题目创建
- **问题描述**：`topic` 字段无 `unique=True`。`save_to_postgres` 先 `filter(topic=...).first()` 检查再 `create()`，两个并发请求可同时通过检查各自创建同名 topic，产生重复数据 + 两套关联 + 两条 Milvus 向量。
- **修改建议**：`Topic.Meta` 加 `unique_together=(("topic",),)` 或字段 `unique=True`；代码用 `try/except IntegrityError` 处理竞态。

### P1-11 ｜ _sync_knowledge_embedding 在 PG 事务内同步写 Milvus，Milvus 故障致 PG 事务回滚

- **位置**：`src/agentv3/capabilities/write.py:118-126,175-176,241`；`src/tools/milvus_client.py:244-250`（insert_knowledge_embedding 无 try-except）
- **涉及范围**：题目创建中知识点 embedding 同步
- **问题描述**：`save_to_postgres` 在 `in_transaction()` 内调用 `_write_knowledge_points` → `_sync_knowledge_embedding` → `milvus.insert_knowledge_embedding()`（与 search 不同，该方法无 try/except，异常直接传播）。Milvus 不可用或写入失败 → 异常传播 → **整个 PG 事务回滚**（含 Topic 主表与所有关联表），违反"PG 是真相源、Milvus 可后补"设计。
- **失败场景**：新建题目含 3 知识点 → PG 写入成功 → 同步第 2 个 embedding 时 Milvus 超时 → 事务回滚 → Topic 及关联全丢，用户见"生成失败"但 LLM 已耗 token。
- **修改建议**：`_sync_knowledge_embedding` 移到事务外（提交后再同步）；或加 try/except 失败仅记日志走 outbox 补偿。

### P1-12 ｜ Master 的 AgentSession.guard() 从未被调用，迭代/时间/预算限制形同虚设

- **位置**：`src/agentv3/master.py:70-76`（create_react_agent 调用）；`src/agentv3/session.py:34-55`（guard 方法）
- **涉及范围**：所有 ReAct Agent 请求
- **问题描述**：`MasterSession.handle()` 配置了 `max_iterations=10`、`max_total_time_ms=60000`、`token_budget=4000`，但 `guard()` 从未被调用（grep 确认）。实际执行由 `create_react_agent` 内置循环控制，默认 `recursion_limit=25`（远超 10）。`record_reasoning()` 也从未调用，`reasoning_chain` 恒空。`agent.ainvoke()` 未传 `recursion_limit`、未用 `asyncio.wait_for` 包超时。
- **失败场景**：LLM 每次响应 5s → Agent 循环 25 次 → 总耗时 125s，远超配置 60s → 占用 LLM 配额与 DB 连接。
- **修改建议**：`agent.ainvoke()` 传 `config={"recursion_limit": max_iterations}`；`asyncio.wait_for` 包整体调用强制时间上限；tool wrapper 中检查预算耗尽拒绝调用。

### P1-13 ｜ Slave 绕过 ToolExecutor，写操作无超时/熔断/日志保护

- **位置**：`src/agentv3/slave.py:57-62`
- **涉及范围**：所有 Slave 写入（save_to_postgres, save_to_milvus）
- **问题描述**：Slave 直接调 `cap.handler(**kwargs)` 而非 `CapabilityRegistry.execute()`，导致 ToolExecutor 的 30s 超时不生效、无熔断、写操作不记 PromptCallLog（可观测性盲区）、内部 LLM 调用不受预算管控。
- **失败场景**：PG 死锁 → `Topic.create` 阻塞 → 无超时 → Slave 挂起 → Master `await slave.execute()` 挂起 → 整个请求无响应。
- **修改建议**：Slave 通过 `CapabilityRegistry.execute()` 调用，复用 ToolExecutor 切面。

### P1-14 ｜ Slave save_to_postgres 失败后仍以空 topic_id 执行 save_to_milvus，污染向量索引

- **位置**：`src/agentv3/slave.py:46-67,84-97`；`src/agentv3/capabilities/write.py:247-289`
- **涉及范围**：Slave 双写流程，PG 写入失败时
- **问题描述**：`execute` 在 `save_to_postgres` 抛异常时加入 `failed` 列表但**继续执行** `save_to_milvus`。此时 `state["_topic_id"]` 未设置，`_build_kwargs` 中 `state.get("_topic_id","")` 返回空串，`save_to_milvus` 不校验直接 `milvus.insert(topic_id="",...)`。
- **失败场景**：PG 唯一约束冲突失败 → 继续 save_to_milvus → Milvus 插入 `topic_id=""` 孤立向量 → 永远无法关联任何 Topic → 污染向量索引影响搜索质量。
- **修改建议**：`_build_kwargs` 校验 `topic_id` 非空否则抛 `ValueError`；或 `save_to_milvus` 开头校验。

### P1-15 ｜ write.py save_to_milvus 补偿链可被完全吞掉，数据永久丢失无告警

- **位置**：`src/agentv3/capabilities/write.py:268-289`
- **涉及范围**：save_to_milvus 失败后的补偿路径
- **问题描述**：Milvus 写失败时补偿两步各自独立 try-except-pass：① 标记 Topic `MILVUS_FAILED`；② 创建 Outbox 补偿记录。两步都失败（如 PG 连接池耗尽）则数据永久丢失无日志无告警，函数却返回 `compensable=True`（谎言）。
- **修改建议**：补偿失败 `logger.error` 记录完整上下文；Outbox 创建失败则返回 `compensable=False`。

### P1-16 ｜ 无登录速率限制/账号锁定，邮件端点可被轰炸

- **位置**：`src/auth/api.py:154-167`（login）、`:174-183`（send-code）
- **涉及范围**：登录暴力破解、邮件轰炸
- **问题描述**：`/login`、`/send-code` 无速率限制。CAPTCHA 本应防护但已因 P0-2 失效。攻击者可自动化无限重试密码；`/send-code` 可向任意邮箱发无限邮件。
- **修改建议**：修复 CAPTCHA；IP+username 滑动窗口限流（5 次/分钟）；连续失败 N 次临时锁定；`/send-code` 每邮箱每分钟 1 次/每天 10 次。

### P1-17 ｜ 全字段 save() 致 lost-update（登录/改密/偏好）

- **位置**：`src/auth/api.py:134,166,275`
- **涉及范围**：用户数据一致性
- **问题描述**：登录读整个 user 改 `token_version` 后 `save()` 全字段 UPDATE，会覆盖读取期间其他请求对其他字段的修改。
- **失败场景**：浏览器 A 登录读到 `preferences_filled=False`，同时浏览器 B 更新偏好写 `True`，A 的 save 晚于 B 则覆盖 B，偏好丢失。
- **修改建议**：用 `User.filter(id=...).update(字段=...)` 精确更新，或 `save(update_fields=[...])`。

### P1-18 ｜ 掌握度自查存在竞态，丢失尝试计数

- **位置**：`src/api/topic_api.py:377-386`
- **涉及范围**：掌握度自查评分记录
- **问题描述**：`get_or_create` → 读 `prev_attempts` → `+1` → `save()` 非原子，并发各自写入相同值；`MasteryAttempt.create` 的 `attempt_number` 重复；`save()` 不带 `update_fields` 全字段覆盖。
- **修改建议**：`filter().update(mastery_attempts=F("mastery_attempts")+1)` 原子递增；`save(update_fields=[...])`。

### P1-19 ｜ 内部异常细节泄露给客户端 + 无全局异常处理器

- **位置**：`src/api/topic_api.py:223,322`；`src/api/interview_api.py:81,134`；`src/main.py`（无 `@app.exception_handler(Exception)`）
- **涉及范围**：Agent 生成、面试分析/回答、题目详情
- **问题描述**：多处 `{e}`/`str(e)` 拼入 HTTP 响应；`get_topic_detail` 的 `except Exception` 把所有异常伪装成 404"Topic 不存在"并附 `str(e)`（DB 宕机时返回 404 而非 500，监控无法发现真实故障）；无全局异常处理器兜底，debug 模式可能返回完整堆栈。
- **修改建议**：对外返回通用错误，`{e}` 仅入日志；区分 404/500；注册全局异常处理器记录 trace_id 返回统一格式。

### P1-20 ｜ 分页参数无边界校验，可触发大查询 DoS

- **位置**：`src/api/topic_api.py:54`
- **涉及范围**：`GET /api/topic/list`
- **问题描述**：`limit: int = 20, offset: int = 0` 无校验，可传 `limit=999999` 拉全表或负数产生未定义行为。
- **修改建议**：`Query(limit=20, ge=1, le=100)`、`Query(offset=0, ge=0)`。

### P1-21 ｜ 手动解析 JSON 请求体，无校验无异常处理

- **位置**：`src/api/topic_api.py:268`、`src/auth/api.py:285`
- **涉及范围**：`POST /api/topic/{id}/status`、`POST /api/auth/preferences`
- **问题描述**：`body = await request.json()` 手动解析，非法 JSON 抛 `JSONDecodeError` 产生 500；`int(body[field])` 抛 `ValueError`；字符串字段无长度限制。
- **修改建议**：定义 Pydantic 模型由 FastAPI 校验。

### P1-22 ｜ 面试 max_rounds 无上界 + resume/jd 无长度限制

- **位置**：`src/api/interview_api.py:23`
- **涉及范围**：面试会话启动
- **问题描述**：`max_rounds: int = 10` 无上界，可传 100000 致每轮多次 LLM 调用资源耗尽；`resume`/`jd` 无长度限制可超长文本耗 token。
- **修改建议**：`field_validator` 限 max_rounds 1-30，限 resume/jd 最大长度。

### P1-23 ｜ 邮件发送静默失败但接口谎报"已发送"，验证码明文打印 stdout

- **位置**：`src/utils/mail.py:13-24`；`src/auth/api.py:174-183,309-310`
- **涉及范围**：邮箱验证码发送
- **问题描述**：`send()` 在 SMTP 未配置或异常时 `except Exception: pass` 不抛错，但路由始终返回"验证码已发送"。用户收不到码却被告知已发送，无法注册。`print(f"[CODE] {code} -> {to}")` 将验证码明文打印 stdout，生产日志泄露验证码。
- **修改建议**：`send()` 返回 bool 或抛异常，路由据实返回；移除 print 改 debug 级日志不含明文。

### P1-24 ｜ 前端 token 刷新队列失效 + 401 静默卡死 + Chat/Interview 绕过拦截器

- **位置**：`TOPICSYSTEM_Web/src/api/request.js:19-49`；`Chat/index.vue:192-200`；`Interview/index.vue:337-341,364-368,407-409`
- **涉及范围**：所有 API 调用在 token 过期场景
- **问题描述**：① `refreshQueue` 声明但从未 push，`isRefreshing=true` 时其余 401 请求被静默 `reject` 丢弃；② 401 且无 refresh_token 时无任何处理，用户被静默卡死；③ Chat/Interview 用原生 `fetch` 绕过 `request` 拦截器，无 401 刷新、无超时、错误处理不一致。
- **修改建议**：`isRefreshing` 时将请求入队待刷新后重放；401 无 refresh_token 则清 token 跳登录；统一用 `request` 实例。

### P1-25 ｜ outbox worker 无 claim/lease，多 worker 并发重复消费

- **位置**：`src/workers/outbox_worker.py:132-134`；`src/main.py:67-71`；`scripts/entrypoint.sh:16`（UVICORN_WORKERS=2）
- **涉及范围**：Outbox 补偿全流程，多实例/多 worker 场景
- **问题描述**：`Outbox.filter(status="PENDING").all()` 无 `FOR UPDATE SKIP LOCKED`、无 claim/lease、无幂等键。每个 uvicorn worker 进程 startup 各起一个 worker，默认 2 个并发。
- **失败场景**：2 worker 同时拉同一批 PENDING → 都 milvus.insert → Milvus 产生重复 topic_id 条目；`retry_count` read-modify-write 非原子，计数不准。
- **修改建议**：`SELECT ... FOR UPDATE SKIP LOCKED LIMIT N` 原子领取，或引入 lease 字段；或将 worker 独立为单实例进程。

### P1-26 ｜ outbox worker fire-and-forget 任务无引用、无优雅关闭、无健康监控

- **位置**：`src/workers/outbox_worker.py:126-147`；`src/main.py:67-71`
- **涉及范围**：Worker 生命周期管理
- **问题描述**：`asyncio.create_task(run_outbox_worker())` 未保存引用（Python 文档明确警告 task 可能被 GC 回收中途消失）；`while True` 无 SIGTERM 处理无退出条件；无健康检查端点暴露 worker 状态。
- **失败场景**：worker 因未捕获异常退出 → task 静默死亡 → outbox 积压无告警。
- **修改建议**：保存 task 引用 + `add_done_callback` 检查异常；worker 心跳机制在 `/ping` 检查；`asyncio.Event` 实现优雅关闭。

### P1-27 ｜ entrypoint.sh 迁移失败静默继续，应用以错误 schema 启动

- **位置**：`scripts/entrypoint.sh:5-14`
- **涉及范围**：全部部署流程
- **问题描述**：`set -e` 被 `if aerich upgrade; then ... else ... fi` 绕过，迁移失败仅打日志后继续启动 uvicorn。`/ping` 只检查进程存活不检查 schema 一致性。
- **失败场景**：新版本含新字段迁移 → `aerich upgrade` 连接超时失败 → 应用以旧 schema 启动 → 访问新字段 API 报 `column does not exist` → 健康检查仍通过 → 流量进入 → 500。
- **修改建议**：迁移失败 `exit 1`；如需容错用 `ALLOW_MIGRATION_FAILURE=1` 显式控制。

### P1-28 ｜ `--forwarded-allow-ips='*'` 信任所有来源 X-Forwarded-For

- **位置**：`scripts/entrypoint.sh:23`
- **涉及范围**：全部 HTTP 请求的客户端 IP 识别
- **问题描述**：配合 `--proxy-headers` 信任任意来源 `X-Forwarded-For`，任何客户端可伪造真实 IP，绕过基于 IP 的限流/访问控制。
- **修改建议**：限制为实际反代 IP（`127.0.0.1` 或内网网段）或环境变量配置。

### P1-29 ｜ settings.py 无启动校验，DATABASE_URL 等关键配置默认空值

- **位置**：`src/config/settings.py:8,18,21-22,28-29`
- **涉及范围**：全部服务启动
- **问题描述**：`DATABASE_URL=""`、`EMBEDDING_API_KEY=""`、`LANGFUSE_*=""`、`RABBITMQ_USER/PASSWORD="guest"` 均空串/弱默认值，Pydantic 不报错。运行时才抛难懂的连接错误。
- **修改建议**：关键字段 `Field(min_length=1)` 或 validator 拒绝空串；`init_db()` 前置 `assert settings.DATABASE_URL`。

### P1-30 ｜ outbox worker 无分页全量加载 PENDING，OOM 风险

- **位置**：`src/workers/outbox_worker.py:132`
- **涉及范围**：Worker 内存稳定性
- **问题描述**：`Outbox.filter(status="PENDING").all()` 一次性加载所有 PENDING 记录，无 limit。Milvus 长时间故障积压时单轮拉取数万条（每条 payload 数 KB）致内存激增 OOM。
- **修改建议**：每轮 `.limit(100)` 分批处理。

### P1-31 ｜ 前端路由守卫管理员校验失效且可被篡改 localStorage 绕过

- **位置**：`TOPICSYSTEM_Web/src/router/index.js:97`；`Login.vue:156`
- **涉及范围**：所有 `requiresAdmin: true` 路由（/user/list, /user/level, /system/menu, /system/permission）
- **问题描述**：守卫从 `localStorage.getItem('user')` 检查 `user.membership_level !== 'admin'`，但 Login.vue 存的 user 对象只有 `{username, email}` 从不含 `membership_level` → 恒 undefined → 守卫恒重定向，管理员页面永久不可达；且 localStorage 可被用户在控制台篡改绕过。
- **修改建议**：登录时从服务端响应存角色；或路由守卫调 `/auth/me` 获取权威角色缓存到 store。

### P1-32 ｜ nginx 缺失安全响应头 + 前端无全局错误处理

- **位置**：`TOPICSYSTEM_Web/nginx.conf:1-26`；`src/main.js:9-12`
- **涉及范围**：所有对外页面/API、整个前端应用
- **问题描述**：nginx 无 CSP/X-Frame-Options/X-Content-Type-Options/HSTS/Referrer-Policy（无法缓解 XSS 与点击劫持），静态资源无缓存头；前端无 `app.config.errorHandler`/`window.onerror`/unhandledrejection，组件内未捕获异常被控制台吞掉，多个组件空 catch 掩盖错误。
- **修改建议**：nginx 加全套安全头与静态资源缓存；main.js 加 errorHandler 与 unhandledrejection 上报。

---

## 3. P2 —— 中等优先级

| # | 标题 | 位置 | 修改建议 |
|---|------|------|----------|
| P2-1 | RabbitMQ 凭据明文嵌入 URL，异常/日志泄露 | `src/common/rabbitmq.py:64` | 改 `connect_robust(host=,login=,password=)` 关键字参数；或 URL 编码密码并脱敏 |
| P2-2 | tag 过滤分页失效，Python 内存过滤 + 硬限 800 | `src/api/topic_api.py:73-75` | tag 过滤下推 DB，正常用 offset/limit |
| P2-3 | `_truncate_json_response` 手工切割 JSON 字符串极度脆弱 | `src/api/topic_api.py:226-253` | 数据结构层面截断，置空长文本字段设 `locked=True` |
| P2-4 | 面试事件发布 fire-and-forget，Task 无引用无错误处理 | `src/api/interview_api.py:146-148` | 保留 task 引用 + 回调处理异常，或 await，或 outbox |
| P2-5 | 面试会话内存字典只增不清，OOM | `src/api/interview_api.py:16` | TTL 过期清理或迁 Redis，summary 后标记可清理 |
| P2-6 | `list_tags` 加载 2000 条完整记录仅取 tags | `src/api/topic_api.py:130` | `.only("tags")` 或 `SELECT DISTINCT` |
| P2-7 | 安全敏感操作用 `random.randint` 非密码学安全 | `src/auth/api.py:145,178` | `secrets.choice(string.digits)`，增加码长 + 限流 |
| P2-8 | 登录响应时间差异致账号枚举（时序攻击） | `src/auth/api.py:159` | 用户不存在时跑一次 dummy bcrypt 消除时序差 |
| P2-9 | `/preferences` 缺输入校验，非法 JSON/类型致 500 | `src/auth/api.py:279-300` | Pydantic 模型校验 |
| P2-10 | 验证码明文打印 stdout + Captcha 表无清理机制 | `src/auth/api.py:310`；`src/models/captcha.py` | 移除 print；定时清理过期记录 |
| P2-11 | deps.py 鉴权依赖为死代码，与中间件双轨鉴权 | `src/auth/deps.py:23-57` | 移除或统一到依赖注入模式 |
| P2-12 | Milvus 客户端几乎所有方法吞异常返回空，失败不可观测 | `src/tools/milvus_client.py` 多处 | except 加 `logging.warning(exc_info=True)`；区分"连接失败"与"无数据"；写失败应抛出 |
| P2-13 | RabbitMQ auto_ack 回调异常被 print 吞没，消息丢失 | `src/common/rabbitmq.py:170-176` | `logging.error` 替代 print；失败入死信队列 |
| P2-14 | RabbitMQ 配置两套来源，`RABBITMQ_USER` vs `RABBITMQ_USERNAME` 不匹配 | `settings.py:28` vs `rabbitmq_config.py:13` | 统一单一配置源与环境变量名 |
| P2-15 | outbox_worker 用 naive `datetime.now()` 与 UTC 不一致 | `src/workers/outbox_worker.py:72,114,139` | 全部 `datetime.now(timezone.utc)` |
| P2-16 | normalize/validate/verify 未用 clean_json，LLM 畸形 JSON 直接崩溃 | `normalize.py:34`、`validate.py:32`、`verify.py:47` | 统一 `json.loads(clean_json(raw))`，抽公共函数 |
| P2-17 | circuit_breaker HALF_OPEN 允许无限请求而非单次探测 | `src/agentv3/circuit_breaker.py:53-54` | HALF_OPEN 限单次探测，任何失败立即回 OPEN |
| P2-18 | token_budget consume() 返回值被忽略，预算不阻断 + 估算值硬编码 | `executor.py:98-99`；`generate.py:73`；`normalize.py:43` | 检查 consume 返回值超支则拒绝；从 LLM 响应取实际 token |
| P2-19 | generate_schemas=True 与 aerich 迁移并存 + 多副本并发 schema 竞态 | `src/main.py:49`；`entrypoint.sh:10` | 生产设 False 仅依赖 aerich；迁移单独 job/leader |
| P2-20 | .env.production 被 git 跟踪 + Docker 镜像未按 digest 固定 | `.gitignore:12-15`；`docker-compose.yml:4,28,45,60` | 加入 .gitignore 改名 .example；镜像按 `@sha256` 固定 |
| P2-21 | 容器无资源限制（memory/CPU limits） | `docker-compose.yml`、`docker-compose.server.yml` | 每服务加 `mem_limit`/`cpus` |
| P2-22 | docker-compose.server.yml 多服务用 host 网络模式降低隔离 | `docker-compose.server.yml:31,50,67,93` | 改 bridge 网络，仅暴露必要端口 |
| P2-23 | 前端依赖全用 caret 范围 + Dockerfile 用 `npm install` 非 `npm ci` + nginx 以 root 运行 | `package.json:12-22`；`TOPICSYSTEM_Web/Dockerfile:6,11` | `npm ci` 严格按 lock；nginx `USER nginx`；加 HEALTHCHECK |
| P2-24 | 前端 topic_list 搜索每次按键直接触发 API 无 debounce；Practice.vue debounce 定时器未清理 | `topic_list.vue:6`；`Practice.vue:163-167` | debounce 300ms；`onUnmounted` 清理定时器 |
| P2-25 | Login.vue 独立 axios 实例 timeout 与全局不一致 | `Login.vue:74` | 抽 `requestNoAuth.js` 统一配置 |
| P2-26 | Topic/embedding_vector 用 TextField 存向量低效 | `src/models/topic.py:36` | 移除或改 BinaryField / pgvector |
| P2-27 | write.py _semantic_dedup alias 写入失败被吞致重复去重 | `write.py:93-96,108-111` | 失败 `logger.warning`；用 `get_or_create` / `ON CONFLICT DO NOTHING` |
| P2-28 | enforce_limit 对含子查询 SQL 不可靠（外层无 LIMIT） | `query_db.py:79-86` | 检查最外层 SELECT 的 LIMIT 或末尾追加 |
| P2-29 | 无 dead-letter 机制，永久失败 outbox 记录无后续处理 | `outbox_worker.py:82-84` | dead-letter 表/状态，支持人工干预重新入队 |

---

## 4. P3 —— 低优先级 / 提示

| # | 标题 | 位置 | 修改建议 |
|---|------|------|----------|
| P3-1 | CORS 硬编码开发地址，allow_methods/headers 过宽 | `src/main.py:21-27` | `CORS_ORIGINS` 配置项；显式列方法/头 |
| P3-2 | payload["sub"] 用 `[]` 可能 KeyError 致 500 | `auth/api.py:231`；`middleware/auth.py:32` | 统一 `.get()` 检查 None |
| P3-3 | Captcha 验证码明文存数据库 | `src/models/captcha.py:12` | 存 hash；风险较低可降级 |
| P3-4 | RabbitMQConsumer.start() busy-wait 循环 | `src/common/rabbitmq.py:242-243` | 用 `asyncio.Event` |
| P3-5 | Milvus 用私有 API `_fetch_handler` | `milvus_client.py:33` | 改 `connections.has_connection` |
| P3-6 | TTLCache / 单例 get_instance() 非线程安全 | `cache.py:18-35`；各 client | asyncio 单线程可接受；多线程加锁 |
| P3-7 | `datetime.utcnow()` 已弃用 | `src/api/topic_api.py:384` | `datetime.now(timezone.utc)` |
| P3-8 | 无全链路 correlation ID | `src/main.py` | 中间件生成/传递 X-Request-ID |
| P3-9 | publish_event MQ 降级到日志仍返回 published=True | `publish_event.py:36-40` | 标记 `degraded: True` |
| P3-10 | score_answer LLM 返回非数值致 TypeError | `score_answer.py:97-100` | `float(...)` 转换或 Pydantic 解析 |
| P3-11 | duplicate.py 回退阈值 0.65 低于正常 0.75 可能误判重复 | `duplicate.py:82-89` | 回退阈值与正常一致或返回 warning 供决策 |
| P3-12 | SMTP 默认 smtp.qq.com:465 与 .env.example gmail:587 不一致；on_event 已废弃；LLMConfig 用 os.getenv 绕过 Pydantic | `mail.py:5-6`；`main.py:54,67`；`llm_config.py:24-26` | 按端口选 SSL/STARTTLS；迁 lifespan；从 settings 读 |

---

## 5. 建议新增的关键回归测试

- `test_query_db_security.py`：SQL 绕过（多语句/注释混淆/CTE/系统表/`pg_sleep`/大笛卡尔积/函数副作用）、超时、超大结果；只读角色无法 DDL/DML。
- `test_auth_matrix.py`：所有路由 × 所有无 token/畸形 token/过期 token/refresh-as-access/禁用用户/改密后旧 token 状态矩阵。
- `test_captcha_race.py`：验证码并发消费、过期、尝试次数、发送限流；邮箱码与邮箱绑定。
- `test_quota_concurrency.py`：双 worker/并发请求配额原子扣减、中间件顺序修复后配额实际生效。
- `test_outbox_concurrency.py`：双 worker 重复消费、租约过期、崩溃恢复、重试耗尽不删业务数据、dead-letter 重放、Milvus 静默降级不被误标 PROCESSED。
- `test_dependency_failures.py`：PostgreSQL/Milvus/RabbitMQ/LLM/SMTP/Embedding 超时与恢复；事件循环不被阻塞。
- `test_config_validation.py`：生产默认密钥/空密钥/非法 URL/错误环境组合；启动失败。
- `test_xss.py`：前端 detail 页对含 HTML 的后端字段转义验证。

---

## 6. 实施顺序建议

### 阶段 A：封堵 P0 安全与数据丢失（1-2 天）
- 修复 P0-2/3（验证码图片化 + 邮箱码绑定）、P0-4/5/6/7/8（鉴权与配额链路）、P0-9（JWT_SECRET 启动校验）。
- 修复 P0-10（凭据脱敏 + 轮换 + 清史）。
- 修复 P0-1（query_db 只读角色 + AST allowlist + 超时 + 不回传错误）。
- 修复 P0-11/12/13（outbox 软删除 + 指数退避 + 静默降级抛异常 + Master 不谎报成功）。
- 修复 P0-14（前端 v-html 转义）。

### 阶段 B：并发与外部依赖治理（2-3 天）
- 修复 P1-4/5/6/7/8（同步阻塞移出事件循环、连接池复用、超时、重连）。
- 修复 P1-1/2/3/10/11/18（缓存失效、原子消费、原子扣减、唯一约束、事务边界）。
- 修复 P1-12/13/14/15（guard 接线、Slave 走 ToolExecutor、空 topic_id 校验、补偿链可观测）。
- 统一 timeout/retry/backoff/circuit-breaker，加入结构化日志与指标。

### 阶段 C：异常处理、可观测性与部署加固（1-2 天）
- 修复 P1-19/21/23（全局异常处理器、Pydantic 校验、不泄露内部错误）。
- 修复 P1-26/27/28/29/30（worker 生命周期、迁移失败保护、forwarded-allow-ips、配置校验、worker 分页）。
- 修复 P2-19/20/21/22/23（schema 迁移、镜像 digest、资源限制、网络隔离、前端构建加固）。

### 阶段 D：前端加固与验收（1-2 天）
- 修复 P1-24/31/32（token 刷新队列、路由守卫、安全响应头、错误上报）。
- 运行 unit/integration/e2e + 并发 + 故障注入测试，证据由 CI 保存。

---

## 7. 完成判定

只有同时满足以下条件，健壮性整改才算完成：

- 14 项 P0 全部修复且各有对应回归测试通过。
- 鉴权矩阵测试覆盖所有路由与所有身份状态；无 token/畸形/过期/refresh-as-access/禁用/改密后旧 token 行为一致。
- query_db 边界为 allowlist + 只读最小权限 + 超时，且不回传原始错误。
- outbox 无因外部短暂故障导致的业务数据物理删除；静默降级不再被误标成功。
- 生产配置无默认/硬编码密钥，日志与 API 响应不泄露内部错误/SQL/凭据。
- 多实例并发与故障恢复演练通过，事件循环在依赖超时期间仍可响应。
- 前端无存储型 XSS，token 刷新与 401 处理在并发场景下正确。

---

*本报告由 GLM 独立审查生成，未参考既有 `ROBUSTNESS_REMEDIATION_PLAN.md` 的结论。所有问题均基于实际代码定位到具体行号，关键 P0/P1 项经核心文件第一手交叉验证。*
