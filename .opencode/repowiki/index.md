# TopicSystem Repo Wiki

> **生成时间**：2026-06-12 00:06:53  
> **基于提交**：168f526（main）  

---

## 文档索引

| 编号 | 文档 | 说明 |
|------|------|------|
| 01 | [项目概览](01-project-overview.md) | 一句话定位、核心业务、项目规模 |
| 02 | [架构设计](02-architecture.md) | 架构风格、系统上下文图、分层设计、ADR |
| 03 | [目录结构](03-directory-structure.md) | 顶层目录、源码详解、关键文件速查 |
| 04 | [技术栈](04-tech-stack.md) | 运行时、框架、数据库、中间件、工具 |
| 05 | [开发设置](05-dev-setup.md) | 环境变量、安装启动、数据库初始化 |
| 06 | [核心模块](06-core-modules.md) | 模块总览、依赖关系、模块间通信 |
| 07 | [API 参考](07-api-reference.md) | 端点清单、请求/响应格式、错误码 |
| 08 | [数据流](08-data-flow.md) | Agent Loop 数据流、持久化路径、缓存策略 |
| 09 | [配置管理](09-configuration.md) | 环境变量词典、加载顺序、配置差异 |
| 10 | [测试策略](10-testing.md) | 测试框架、覆盖率、运行方式、约定 |
| 11 | [编码规范](11-coding-conventions.md) | 代码风格、命名规范、Linting |
| 12 | [错误处理](12-error-handling.md) | 错误分级、降级路径、Outbox 补偿 |
| 13 | [认证与授权](13-authentication.md) | JWT 认证、配额管理、安全措施 |
| 14 | [数据库设计](14-database.md) | 数据模型、ER 图、迁移策略 |
| 15 | [部署运维](15-deployment.md) | 部署架构、CI/CD、容器化、监控 |

---

## 项目画像

- **项目名**：TopicSystem v3
- **语言**：Python 3.12（后端）+ Vue 3 / TypeScript（前端）
- **框架**：FastAPI + LangGraph ReAct Agent
- **数据库**：PostgreSQL 16（Tortoise ORM）+ Milvus 2.4（向量）
- **容器化**：Docker Compose（6 服务）
- **测试**：pytest + pytest-asyncio
- **源文件数**：~97 个 Python + ~7074 个 JS/TS（含 node_modules）
