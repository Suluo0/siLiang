# TopicSystem Repo Wiki

> **生成时间**：2026-06-18 15:04:06，**最近更新**：2026-06-21（题库页改造 + 交互契约文档 + 修正前端语言/部署链路）
> **基于提交**：`b2fadb8`（main）
> **生成方式**：Hermes Agent 内置 `repo-wiki` skill(从 OpenCode 迁移)

---

## 文档索引

| 编号 | 文档 | 说明 |
|------|------|------|
| 01 | [项目概览](01-project-overview.md) | 一句话定位、核心业务、入口、规模 ✅ |
| 02 | [架构设计](02-architecture.md) | Master-Slave Agent + AOP 切面 + 中间件三层 ✅ |
| 03 | [目录结构](03-directory-structure.md) | 顶层 / 后端 src / 前端 / 部署 ✅ |
| 04 | 技术栈 | Python 3.13 + FastAPI + Tortoise + Milvus ⏳ 待生成 |
| 05 | 开发设置 | uv + pytest + topic_test 测试库 ⏳ 待生成 |
| 06 | 核心模块 | 16 个 capability + 5 大模块依赖图 ⏳ 待生成 |
| 07 | API 参考 | 5 大路由 + 4 套面试 API ⏳ 待生成（端点速查见 16） |
| 08 | 数据流 | 出题流水线 + 面试 Loop + 双写 ⏳ 待生成 |
| 09 | 配置管理 | settings 单源 + .env 三层 ⏳ 待生成 |
| 10 | 测试策略 | 150 passed / 56% cov / topic_test 库 ⏳ 待生成 |
| 11 | 编码规范 | 红线 1.1~7.2 + ruff ⏳ 待生成 |
| 12 | 错误处理 | Outbox 补偿 + 熔断 + 结构化日志 ⏳ 待生成 |
| 13 | 认证授权 | JWT + slowapi + 中间件三层 ⏳ 待生成 |
| 14 | 数据库设计 | 30 张表 + ER 图 + Milvus 集合 ⏳ 待生成 |
| 15 | 部署运维 | 后端 docker-compose.server + 前端宿主机 nginx + GitHub Actions ⏳ 待生成 |
| 16 | [前后端交互契约](16-frontend-backend-contract.md) | **路由 → API → 数据库** 端到端映射表 ✅ |

> ⏳ 标记的 04–15 文档为上次 wiki 生成中断时未落地的部分（当前仅 01/02/03/16 已生成）。
> 跑一次完整 wiki（关键词触发 `repo-wiki` skill）即可补齐，已纳入下方 `wiki-state.json` 的 `pendingDocs`。

---

## 项目画像

- **项目名**：TopicSystem v4(模拟面试子系统已上线)
- **后端**：Python 3.13 / FastAPI 0.131 / Tortoise ORM 0.25 / Milvus 2.4 / pgvector pg16
- **前端**：Vue 3 + **JavaScript（纯 JS，无 TypeScript）** + Element Plus 2.13.7(`TOPICSYSTEM_Web/`)
- **部署**：后端 docker-compose(`siliang-pg / siliang-milvus / siliang-etcd / siliang-minio / siliang-app`)；前端宿主机 nginx serve `/var/www/siliang`；CI 用 **GitHub Actions**（`deploy.yml` / `deploy-frontend.yml` / `test.yml`，无 Jenkinsfile），host 115.190.161.132
- **后端源文件**:100 个 `.py`(本地)、117 个(服务器,详见 [diff-local-vs-server.md](../diff-local-vs-server.md))
- **测试**:20 个测试文件、**150 passed / 5 xfailed / 56% coverage**
- **生产数据**:1226 道题目 / 3948 core_concept / 2315 derivative / 30 张表

## 状态文件

- `wiki-state.json` 记录**已生成文档**(01/02/03/16)对应源模块 + 真实 md5 hash,下次跑 wiki 触发**最小增量更新**(只重生成命中改动的文档)
- `pendingDocs` 列出尚未生成的 04–15,跑一次完整 wiki 即补齐
- `documentMappings` 已采用**触发式**(`triggers`/`modules`)而非全量 `["*"]`,落实最小更新原则
- 用户可手工编辑任何文档,增量算法对比 hash 时会保留手动修改并告警

## 维护方式

- 增量更新:在工作目录里说"更新 wiki"或"跑一遍 repo wiki"
- 强制全量:说"force 全量重做 wiki"
- 查看状态:说"wiki 状态"

提交本目录到 git 一起 review。
