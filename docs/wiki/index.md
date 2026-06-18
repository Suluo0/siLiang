# TopicSystem Repo Wiki

> **生成时间**：2026-06-18 15:04:06
> **基于提交**：`7648ad3`（main）+ 未提交改动(测试基础设施 v1)
> **生成方式**：Hermes Agent 内置 `repo-wiki` skill(从 OpenCode 迁移)

---

## 文档索引

| 编号 | 文档 | 说明 |
|------|------|------|
| 01 | [项目概览](01-project-overview.md) | 一句话定位、核心业务、入口、规模 |
| 02 | [架构设计](02-architecture.md) | Master-Slave Agent + AOP 切面 + 中间件三层 |
| 03 | [目录结构](03-directory-structure.md) | 顶层 / 后端 src / 前端 / 部署 |
| 04 | [技术栈](04-tech-stack.md) | Python 3.13 + FastAPI + Tortoise + Milvus |
| 05 | [开发设置](05-dev-setup.md) | uv + pytest + topic_test 测试库 |
| 06 | [核心模块](06-core-modules.md) | 16 个 capability + 5 大模块依赖图 |
| 07 | [API 参考](07-api-reference.md) | 5 大路由 + 4 套面试 API |
| 08 | [数据流](08-data-flow.md) | 出题流水线 + 面试 Loop + 双写 |
| 09 | [配置管理](09-configuration.md) | settings 单源 + .env 三层 |
| 10 | [测试策略](10-testing.md) | **150 passed / 56% cov / topic_test 库** |
| 11 | [编码规范](11-coding-conventions.md) | 红线 1.1~7.2 + ruff |
| 12 | [错误处理](12-error-handling.md) | Outbox 补偿 + 熔断 + 结构化日志 |
| 13 | [认证授权](13-authentication.md) | JWT + slowapi + 中间件三层 |
| 14 | [数据库设计](14-database.md) | 30 张表 + ER 图 + Milvus 集合 |
| 15 | [部署运维](15-deployment.md) | docker-compose.server + Jenkinsfile |

---

## 项目画像

- **项目名**：TopicSystem v4(模拟面试子系统已上线)
- **后端**：Python 3.13 / FastAPI 0.131 / Tortoise ORM 0.25 / Milvus 2.4 / pgvector pg16
- **前端**：Vue 3 + TypeScript + Element Plus(`TOPICSYSTEM_Web/`)
- **部署**：docker-compose(`siliang-pg / siliang-milvus / siliang-etcd / siliang-minio / siliang-app`),Jenkinsfile,host 115.190.161.132
- **后端源文件**:100 个 `.py`(本地)、117 个(服务器,详见 [diff-local-vs-server.md](../diff-local-vs-server.md))
- **测试**:20 个测试文件、**150 passed / 5 xfailed / 56% coverage**
- **生产数据**:1226 道题目 / 3948 core_concept / 2315 derivative / 30 张表

## 状态文件

- `wiki-state.json` 记录每份文档对应的源模块 + md5 hash,下次 `/wiki` 触发增量更新
- 用户可手工编辑任何文档,增量算法会保留手动修改并告警

## 维护方式

- 增量更新:在工作目录里说"更新 wiki"或"跑一遍 repo wiki"
- 强制全量:说"force 全量重做 wiki"
- 查看状态:说"wiki 状态"

提交本目录到 git 一起 review。
