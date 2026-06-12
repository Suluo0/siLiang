# 配置管理

> **生成时间**：2026-06-12 00:06:53  
> **基于提交**：168f526（main）  
> **覆盖模块**：全部

---

## 配置文件

| 文件 | 用途 | 环境 |
|------|------|------|
| `src/config/settings.py` | 主配置（Pydantic BaseSettings） | 全部 |
| `src/config/database_db.py` | Tortoise ORM / Aerich 数据库配置 | 全部 |
| `src/config/llm_config.py` | LLM 模型注册与配置 | 全部 |
| `src/config/rabbitmq_config.py` | RabbitMQ 连接配置 | 全部 |
| `.env` | 环境变量文件 | 全部 |
| `docker-compose.yml` | Docker Compose 环境变量注入 | 开发/生产 |
| `aerich.ini` | Aerich 迁移路径配置 | 全部 |

## 环境变量词典

### 主配置 (`Settings`)

| 变量名 | 类型 | 说明 | 默认值 | 必填 | 敏感 |
|--------|------|------|--------|------|------|
| `DATABASE_URL` | string | PostgreSQL 连接串 | `postgres://postgres:Xswl1139@localhost:5432/topic` | 是 | 是 |
| `MILVUS_HOST` | string | Milvus 主机 | `localhost` | 是 | 否 |
| `MILVUS_PORT` | int | Milvus 端口 | `19530` | 是 | 否 |
| `MILVUS_COLLECTION` | string | Milvus Collection 名 | `topic_embeddings` | 否 | 否 |
| `LLM_API_KEY` | string | LLM API Key（备用） | `""` | 否 | 是 |
| `LLM_API_BASE` | string | LLM API 基础路径 | `https://api.minimaxi.com/v1` | 否 | 否 |
| `LLM_MODEL` | string | 默认 LLM 模型 | `MiniMax-M2.7` | 否 | 否 |
| `EMBEDDING_MODEL` | string | Embedding 模型名 | `BAAI/bge-large-zh-v1.5` | 否 | 否 |
| `EMBEDDING_DEVICE` | string | Embedding 计算设备 | `cpu` | 否 | 否 |
| `LANGFUSE_PUBLIC_KEY` | string | LangFuse 公钥 | `""` | 否 | 是 |
| `LANGFUSE_SECRET_KEY` | string | LangFuse 密钥 | `""` | 否 | 是 |
| `LANGFUSE_HOST` | string | LangFuse 服务地址 | `https://cloud.langfuse.com` | 否 | 否 |
| `RABBITMQ_HOST` | string | RabbitMQ 主机 | `localhost` | 否 | 否 |
| `RABBITMQ_PORT` | int | RabbitMQ 端口 | `5672` | 否 | 否 |
| `RABBITMQ_USER` | string | RabbitMQ 用户 | `guest` | 否 | 否 |
| `RABBITMQ_PASSWORD` | string | RabbitMQ 密码 | `guest` | 否 | 是 |
| `RABBITMQ_VHOST` | string | RabbitMQ 虚拟主机 | `/` | 否 | 否 |

### LLM 客户端环境变量 (`LLMClient`)

| 变量名 | 类型 | 说明 | 默认值 | 必填 | 敏感 |
|--------|------|------|--------|------|------|
| `TS_DS_APIKEY` | string | DeepSeek API Key（主） | — | 是 | 是 |
| `API_ADDRESS` | string | LLM API 地址 | `https://api.deepseek.com/v1` | 否 | 否 |
| `API_MODEL` | string | LLM 模型名 | `deepseek-chat` | 否 | 否 |

### 邮件配置（`auth/api.py`）

| 变量名 | 类型 | 说明 | 默认值 | 必填 | 敏感 |
|--------|------|------|--------|------|------|
| `SMTP_USER` | string | QQ 邮箱地址 | `""` | 注册功能必填 | 否 |
| `SMTP_PASS` | string | QQ 邮箱授权码 | `""` | 注册功能必填 | 是 |

## 配置加载顺序

```
1. Pydantic BaseSettings 从 .env 文件加载
2. 环境变量覆盖 .env 文件
3. 代码默认值兜底
```

`Settings` 类继承 `pydantic_settings.BaseSettings`，自动从 `.env` 文件和系统环境变量加载。

## 环境差异

| 配置项 | 开发 | Docker | 生产 |
|--------|------|--------|------|
| `DATABASE_URL` | `postgres://postgres:xxx@localhost:5432/topic` | `postgres://topic_app:xxx@postgres:5432/topic` | [待补充] |
| `MILVUS_HOST` | `localhost` | `milvus` (Docker 服务名) | [待补充] |
| `EMBEDDING_DEVICE` | `cpu` | `cpu` | [待补充] |
| `LLM_MODEL` | `deepseek-chat` | `deepseek-chat` | [待补充] |
| Debug 日志 | `True` | [待补充] | `False` |

## 功能开关（Feature Flags）

当前代码中未发现显式的 Feature Flag 机制。以下是通过配置间接控制的行为：

| 行为 | 控制方式 |
|------|----------|
| Embedding 降级（返回零向量） | `sentence-transformers` 库不可用时自动降级 |
| Milvus 降级（跳过向量检索） | Milvus 不可达时返回空结果 |
| L2 语义去重跳过 | Milvus 或 sentence-transformers 不可用时降级为 L1 only |

## LLM 模型注册

`src/config/llm_config.py:LLMConfig` 预注册模型：

| 模型名 | Temperature | Max Tokens | Timeout | 说明 |
|--------|-------------|------------|---------|------|
| `MiniMax-M2.7` | 0.7 | 4096 | 120s | 默认生成模型 |
| `gpt-4-turbo` | [待补充] | [待补充] | [待补充] | 备用 |
| `gpt-4o` | [待补充] | [待补充] | [待补充] | 备用 |
| `gpt-3.5-turbo` | [待补充] | [待补充] | [待补充] | 备用 |
