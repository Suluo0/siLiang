# 项目概览

> **生成时间**：2026-06-12 00:06:53  
> **基于提交**：168f526（main）  
> **覆盖模块**：全部

---

## 一句话定位

基于 LangGraph ReAct Agent 的 AI 面试题自动生成与召回系统——Agent 自主编排 8 个原子能力，根据召回质量自动分支（命中直接返回 / 未命中兜底生成），全链路 OpenTelemetry + LangFuse 追踪。

## 核心业务

1. **面试题智能生成**：用户输入技术概念，系统通过 LLM 从零生成完整结构化面试题（含前置知识、核心概念、代码示例、陷阱提示、相似问题、进阶问题、参考资料等 9 张关联表数据）
2. **向量召回优先**：优先从 Milvus 向量数据库召回已有题目，通过 5 层防呆校验 + 双分数机制保证召回质量，命中直接返回避免重复生成
3. **用户学习系统**：支持用户标记题目掌握状态（mastered/learning）、每日学习目标、配额管理（20 题/天 + 5 次 Agent 对话/天）
4. **用户认证**：JWT 双 Token（Access + Refresh），邮箱验证码注册，bcrypt 密码哈希，token_version 强制下线

## 入口点

| 入口 | 路径 | 说明 |
|------|------|------|
| API 入口 | `POST /api/v3/topic/generate` | Agent Loop 生成面试题 |
| API 入口 | `GET /api/v1/topic/list` | 分页查询题库 |
| API 入口 | `POST /api/auth/register` | 用户注册 |
| Web 入口 | `http://localhost` (port 80) | Vue 3 SPA 前端 |
| 健康检查 | `GET /ping` | 服务可用性检查 |

## 关键依赖

| 服务/组件 | 用途 | 重要性 |
|-----------|------|--------|
| DeepSeek API | LLM 推理（归一化、生成、校验） | 核心 |
| PostgreSQL 16 | 关系数据持久化 | 核心 |
| Milvus 2.4 | 向量检索与语义召回 | 核心 |
| bge-large-zh-v1.5 | 中文 Embedding 编码 | 核心 |
| Etcd + MinIO | Milvus 元数据与对象存储 | 重要 |
| LangFuse | LLM 链路追踪 | 重要 |
| RabbitMQ | 消息队列（预留） | 辅助 |

## 项目规模

- 源文件数：~97 个 Python 文件 + ~174 个前端源文件（不含 node_modules）
- 主要语言：Python（后端）、TypeScript/JavaScript（前端）
- 包管理器：Poetry（Python）、npm（前端）
- 构建工具：Vite（前端）

## 快速导航

- [架构设计](02-architecture.md)
- [目录结构](03-directory-structure.md)
- [技术栈](04-tech-stack.md)
- [开发设置](05-dev-setup.md)
