# 项目概览

> **生成时间**：2026-06-18 15:04:06
> **基于提交**：`7648ad3`(main)
> **覆盖模块**：全局

---

## 一句话定位

TopicSystem 是一个**面向 Java 后端面试的 AI 出题与模拟面试系统**:基于 LLM + 知识库,自动生成结构化面试题(含核心概念/前置知识/衍生/扩展/评分锚点等 9 类挂载实体),并在此基础上提供**多轮模拟面试 + 五维评分 + 简历/JD 匹配**的完整闭环。

## 核心业务

| 业务线 | 说明 |
|---|---|
| **题目生成** | 用户输入主题或方向 → Agent 编排 16 项能力 → 产出题目 + 9 类挂载实体 → 双写 PG + Milvus |
| **模拟面试** | 创建房间 → 选择面试官 persona → 回答 → 五维评分 → 路由(衍生/扩展/前置/总结) → 生成报告 |
| **简历/JD 分析** | 上传简历或 JD → Agent 提取上下文 → 匹配度评分 → 生成针对性追问 |
| **用户与配额** | JWT 登录 + 邮件验证码 + 多级用户(LV0/LV1/...) + 配额扣减中间件 |
| **掌握度跟踪** | mastery_attempt 表记录每次答题,支撑 user_topic_status 状态机 |

## 入口点

| 入口 | 路径 | 说明 |
|---|---|---|
| 后端 ASGI | `src/main.py` | FastAPI app,注册 5 大路由 + Tortoise lifespan + 鉴权/配额中间件 |
| 前端 SPA | `TOPICSYSTEM_Web/src/main.js` | Vue 3 + Vite（纯 JS，非 TS）,生产构建产物由宿主机 Nginx 提供 |
| Worker 进程 | `src/workers/outbox_worker.py` | 消费 outbox 表,补偿 LLM/邮件/RabbitMQ 失败任务 |
| 题库批量脚本 | `scripts/long_run_gen.py` / `scripts/expand_topics.py` / `scripts/iterative_coverage.py` | 长跑批量出题,从覆盖率出发反向补题 |

## 关键依赖

| 服务/组件 | 用途 | 重要性 |
|---|---|---|
| PostgreSQL 16 (pgvector) | 30 张表的关系数据 + agent_trace + outbox | 核心 |
| Milvus 2.4 | topic_embeddings 向量集合(查重 + 语义检索) | 核心 |
| etcd 3.5 + MinIO | Milvus 元数据 + 对象存储 | 核心(支撑 Milvus) |
| DeepSeek API | 主推理模型(`deepseek-chat`) | 核心 |
| SiliconFlow Embedding | `BAAI/bge-large-zh-v1.5` 向量化 | 核心 |
| RabbitMQ | 异步消息(目前由 outbox 表+worker 兜底) | 重要 |
| Langfuse | 链路追踪(`langfuse>=2.0`) | 辅助 |
| QQ SMTP | 邮件验证码(`297027989@qq.com`) | 辅助 |

## 项目规模

| 指标 | 数值 |
|---|---|
| 后端 Python 源文件 | **100** 个(本地)/ **117** 个(服务器,详见 [diff](../diff-local-vs-server.md)) |
| 前端 Vue 文件 | ~30 个 `.vue` + JS 模块（**纯 JavaScript，无 TypeScript / 无 tsconfig**） |
| 数据库表 | **30** 张(线上)/ **24** 张(本地 schema 略旧) |
| 测试文件 | **20** 个 `.py`(`tests/*.py`) |
| 测试用例 | **150 passed / 5 xfailed / 4 xpassed**,覆盖率 **56.16%** |
| 生产数据 | **1226** 道题目 / 3948 core_concept / 2315 derivative / 3678 evaluation_anchor |
| 主要语言 | Python 3.13 / JavaScript (ES2022) / Vue 3 |
| 包管理 | uv (本地) / Poetry(服务器,见 [diff](../diff-local-vs-server.md)) |

## 快速导航

- [架构设计](02-architecture.md) — Master-Slave Agent / AOP / 中间件三层
- [目录结构](03-directory-structure.md)
- [技术栈](04-tech-stack.md)
- [开发设置](05-dev-setup.md) — 本地起 PG + topic_test 测试库
- [API 参考](07-api-reference.md) — 5 大路由分组 + 端点表
- [测试策略](10-testing.md) — Makefile + Github Actions + pre-commit
