# TopicSystem 项目进度总结

> 生成时间: 2026-06-11

---

## ✅ 已完成

### v3 Agent Loop 架构
- [x] 8 个自举 Capability（normalize/duplicate/search/verify/generate/validate/save_pg/save_milvus）
- [x] Master/Slave 会话隔离
- [x] ToolExecutor 运行时保护（precondition→timeout→sanitize→schema）
- [x] LangGraph ReAct Agent 模型原生 tool calling
- [x] PromptBuilder 动态能力描述注入

### 鉴权系统
- [x] JWT 登录（用户名+密码+CAPTCHA）
- [x] 注册：CAPTCHA→邮箱验证码→自动登录
- [x] 密码规则：8位+字母+数字 / 用户名：6位+字母开头
- [x] 全局鉴权中间件（AOP）
- [x] Token 版本控制（改密/新设备登录踢出旧 token）
- [x] 配额系统（topic_credits + agent_credits）
- [x] 内容截断 + 蒙版遮罩（quota=0 或未登录）
- [x] 会员升级 Modal（免费 vs 高级对比）
- [x] 多设备登录互踢（token_version 递增）

### 前端
- [x] 登录/注册页（CAPTCHA + 邮箱验证码 + 协议勾选）
- [x] 题库信息流三列布局
- [x] Dashboard 四卡片真实数据（已登录）/ "登录后查看"（未登录）
- [x] 未登录可访问主页（移除强制登录路由守卫）
- [x] 用户中心页（账户信息 + 偏好设置 + 改密）
- [x] 用户协议/隐私协议页面
- [x] 注册偏好弹窗（目标岗位 + 学习偏好 + 经验水平 + 每日目标）
- [x] Header 右上角访客菜单（登录/注册 vs 用户中心/退出）

### 数据库
- [x] User: membership_level, target_position, learning_preference, experience_level, today_target, preferences_filled
- [x] UserTopicStatus 中间表（user + topic + mastered/learning）
- [x] JobPosition 岗位表（10 个种子数据）
- [x] UserQuota 配额表
- [x] AgentTrace + PromptCallLog 追踪表

### 代码质量
- [x] 清理 13 个幽灵文件（-1874 行）
- [x] LLMClient 统一（+ astream 流式输出）
- [x] write.py 修复：写入 8 关联表 + Outbox 补偿
- [x] gen_skill.md 重设计（+ one_liner 一句话回答）
- [x] CompatibleJSONField 修复（asyncpg JSONB 兼容）
- [x] 14/14 API 自动化测试通过

### 部署
- [x] 云服务器 115.190.161.132 部署（PG + App + Nginx）
- [x] DB 三角色权限（topic_admin / topic_app / topic_read）
- [x] Nginx 反代 + SPA 静态文件
- [x] Docker 镜像加速配置
- [x] docker-compose.server.yml（host 网络模式）
- [x] .env.production 模板

---

## ❌ 未完成

### 数据补偿
- [ ] 本地 1064 题迁移至服务器（one_liner + 8 关联表回填）
  - 原因：Docker 容器内代理问题导致 LLM 调用断连
  - 方案：宿主机直接跑 `scripts/backfill_relations.py`
- [ ] 向量数据（Milvus）——空库
  - 原因：Docker 未装 sentence-transformers + Milvus 镜像拉取失败
  - 方案：服务器装 bge 量化版 + 拉 Milvus 镜像

### Milvus
- [ ] 服务器 Milvus 镜像拉取（被墙）
  - 方案：用 daocloud mirror 或 scp 本地镜像
- [ ] bge-large-zh INT8 量化部署（省内存 60%）

### CI/CD
- [ ] GitHub Actions 自动化部署
- [ ] `deploy.sh` 脚本完善（aerich 迁移在服务器容器内有问题）

### 前端功能
- [ ] 模拟面试页面（面经/模拟面试/交流社区——全部"敬请期待"）
- [ ] 题库：点击标记"已掌握/未掌握"按钮（后端 API 已有）
- [ ] 题库：按用户水平/偏好偏好排序（后端已存，前端未接）
- [ ] 用户中心：简历上传（模拟面试需要）
- [ ] Chat 页面：显示消息历史 + streaming 输出

### 架构
- [ ] Phase 3 解耦（中间件 PUBLIC_PATHS 硬编码、N+1 查询、sync LLM）
- [ ] tracer.py 接 OpenTelemetry/LangFuse 导出

---

## ⚠️ 注意事项

### 安全
1. **JWT SECRET** — `auth/jwt.py` 中写死了 `topicsystem-jwt-secret-change-in-production-2026`，生产环境必须更换
2. **DB 密码** — `.env.production` 中 postgres 密码仅用于开发，生产换强密码
3. **DB 角色密码** — `init_db_roles.sql` 中三个角色密码均为示例，生产务必更换
4. **API Key** — `.env` 中的 TS_DS_APIKEY 不可提交到 Git（已加入 .gitignore）

### 运营
1. **DeepSeek API 配额** — 每次生成约 3000 token，批量回填 1064 题约消耗 $0.3
2. **邮件发送** — QQ SMTP 已配置，需确保 `SMTP_USER`/`SMTP_PASS` 在服务器 `.env` 中
3. **免费用户 20 次访问限制** — 目前本地开发环境已耗尽，服务器从 0 开始

### 技术债务
1. **v2 管道代码** — `src/agent/` 目录已清理依赖但文件仍存在（topic_api_v2.py 已从 main.py 移除）
2. **Milvus OOM 风险** — 4GB 服务器需 bge 量化才能全组件部署
3. **aerich 迁移** — 本地 + 服务器均未成功初始化，目前依赖 `generate_schemas=True`
4. **HTTPS** — 服务器未启用 SSL，生产需要

### 关键 API 端点

| 端点 | 鉴权 | 说明 |
|------|------|------|
| `POST /api/v3/topic/generate` | 需要 | Agent Loop 生成 |
| `GET /api/v1/topic/list` | 公开 | 题库列表 |
| `GET /api/v1/topic/tags` | 公开 | 标签列表 |
| `GET /api/v1/topic/positions` | 公开 | 岗位列表 |
| `POST /api/auth/register` | 公开 | 注册 |
| `POST /api/auth/login` | 公开 | 登录 |
| `GET /api/auth/me` | 需要 | 当前用户 |
| `POST /api/auth/preferences` | 需要 | 更新偏好 |
| `GET /api/v1/topic/dashboard/stats` | 公开 | Dashboard 统计 |
| `GET /api/v1/topic/{id}` | 公开 | 题目详情（未登录截断） |

### 下次 session 建议顺序

1. 服务器数据补偿（backfill_relations.py — 在宿主机执行）
2. bge 量化 + Milvus 部署
3. 模拟面试页面开发
4. 用户偏好驱动的内容排序
5. HTTPS + 生产安全加固
