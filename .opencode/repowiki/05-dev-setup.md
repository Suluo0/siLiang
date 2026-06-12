# 开发设置

> **生成时间**：2026-06-12 00:06:53  
> **基于提交**：168f526（main）  
> **覆盖模块**：全部

---

## 前置条件

| 工具 | 最低版本 | 检查命令 |
|------|----------|----------|
| Python | 3.12 | `python --version` |
| Docker Desktop | 最新版 | `docker --version` |
| Poetry | 最新版 | `poetry --version` |
| Node.js (前端开发) | 18+ | `node --version` |

## 环境变量

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `TS_DS_APIKEY` | DeepSeek API Key | — | 是 |
| `API_ADDRESS` | LLM API 地址 | `https://api.deepseek.com/v1` | 否 |
| `API_MODEL` | LLM 模型名 | `deepseek-chat` | 否 |
| `DATABASE_URL` | PostgreSQL 连接串 | `postgres://postgres:Xswl1139@localhost:5432/topic` | 否 |
| `MILVUS_HOST` | Milvus 地址 | `localhost` | 否 |
| `MILVUS_PORT` | Milvus 端口 | `19530` | 否 |
| `LLM_API_KEY` | LLM API Key（备用） | `""` | 否 |
| `LANGFUSE_PUBLIC_KEY` | LangFuse 公钥 | `""` | 否 |
| `LANGFUSE_SECRET_KEY` | LangFuse 密钥 | `""` | 否 |
| `RABBITMQ_HOST` | RabbitMQ 地址 | `localhost` | 否 |
| `SMTP_USER` | QQ 邮箱地址（发送验证码） | `""` | 否 |
| `SMTP_PASS` | QQ 邮箱授权码 | `""` | 否 |

> 完整的环境变量清单详见 [09-configuration.md](09-configuration.md)

## 安装与启动

```bash
# 1. 克隆项目
git clone <repo-url> && cd TopicSystem

# 2. 配置 API Key
export TS_DS_APIKEY=sk-xxx

# 3. 启动全部 Docker 服务（PG + Etcd + MinIO + Milvus + App + Web）
docker compose up -d

# 4. 验证
curl http://localhost:8000/ping        # {"status":"ok","service":"TopicSystem"}
curl http://localhost:8000/            # {"service":"TopicSystem v3","status":"ok","capabilities":8}

# 5. 访问前端
open http://localhost
```

```bash
# 本地开发（不依赖 Docker）
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 确保本地 PostgreSQL + Milvus 运行中
# 3. 启动 FastAPI 开发服务器
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# 4. 启动前端开发服务器
cd TOPICSYSTEM_Web && npm install && npm run dev
```

## 数据库初始化

```bash
# Aerich 数据库迁移（Docker 启动时自动执行）
aerich upgrade

# 初始化 Milvus Collection Schema
python scripts/init_milvus.py

# 导入种子数据（996 道面试题）
python scripts/seed_data.py
```

## 常用命令

| 命令 | 说明 |
|------|------|
| `docker compose up -d` | 启动全部服务 |
| `docker compose down` | 停止全部服务 |
| `docker compose logs -f app` | 查看后端日志 |
| `uvicorn src.main:app --reload` | 本地后端开发服务器 |
| `pytest tests/ -v` | 运行所有测试 |
| `pytest tests/test_agentv3.py -v` | 运行 Agent v3 测试 |
| `pytest tests/test_agentv3.py -v -k "not GoldenDataset"` | 跳过 Golden Dataset 测试（无外部 API 依赖） |
| `ruff check src/` | 代码检查 |
| `cd TOPICSYSTEM_Web && npm run dev` | 前端开发服务器 |
| `cd TOPICSYSTEM_Web && npm run build` | 前端生产构建 |

## 开发工作流

- **分支策略**：基于 `main` 分支开发，功能分支合并
- **CI/CD**：Jenkinsfile 定义（Checkout → Test → Build → Deploy）
- **数据库迁移**：Docker 启动时自动执行 `aerich upgrade`
- **测试要求**：提交前运行 `pytest tests/ -v -k "not GoldenDataset"` 确保基础测试通过
