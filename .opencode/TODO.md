# TopicSystem 项目进度总结

> 更新: 2026-06-12

---

## ✅ 已完成

### 安全 (P0)
- [x] JWT SECRET 环境变量化（本地+服务器均已迁移）
- [x] DB 密码模板已标记生产必换警告
- [x] API Key 已验证未被提交到 Git
- [x] `.env` 已加入 `.gitignore`

### 基础设施 (P1)
- [x] Milvus 部署（etcd + minio + milvus standalone，host 网络模式）
- [x] 硅基流动 BGE v1.5 API 替代本地模型（零 PyTorch 依赖，零本地显存）
- [x] Embedding API 密钥环境变量化（`EMBEDDING_API_KEY`）
- [x] Milvus 三 collection：`topic_embeddings` / `knowledge_embeddings` / `table_schemas`
- [x] Milvus 连接持久化修复（`_ensure_connection` 替代临时连接）
- [x] HNSW 索引生命周期正确（先插数据再建索引，不再 `drop_collection`）

### DB Schema 重构
- [x] 4 关联表从 `content` 升级为 `knowledge_id(FK) + importance`
- [x] 新建 `knowledge_dict`（知识点词典，name UNIQUE 自动去重）
- [x] 新建 `knowledge_alias`（同义知识点映射，如 "MVCC"→"多版本并发控制"）
- [x] `topic_evaluation_anchor` 从 `content` 拆为 `question` + `expected_answer`
- [x] `topic` 主表加 `tech_domain` 字段
- [x] write.py 修复 importlib 动态导入 bug（改为直接 import，8 表全空问题修复）

### Skill 体系
- [x] gen_skill 拆分为 `gen_topic_content.md` + `gen_topic_topology.md`
- [x] topology skill 引入 2 组 fewshot 示例 + 严格 type 决策树
- [x] generate.py 改为两阶段 LLM 调用（内容→拓扑）
- [x] 新建 `query_skill.md`（NL→SQL，含 7 组 fewshot）
- [x] 新建 `validate_topic.md`（求职者+面试官双维度质量审计）
- [x] schema_manager 动态表结构检索（Milvus table_schemas collection）

### Capability
- [x] 新增 `query_database` capability（NL→SQL→安全校验→asyncpg 执行）
- [x] SQL 安全校验：只允许 SELECT，禁止 DDL/DML，自动 LIMIT，禁多语句
- [x] 知识点去重三层：精确匹配 → alias 查询 → BGE 语义 + LLM 确认

### 部署 & 测试
- [x] 全链路 10 题端到端测试通过（3 领域：后端/数据库/消息队列）
- [x] API 级测试（`POST /api/v3/topic/generate`，30 行脚本零业务逻辑）
- [x] 知识图谱双向验证：HashMap→红黑树→并发→锁的逻辑推导链成立
- [x] executor.py `str(kwargs).get()` bug 修复
- [x] 知识点去重单元测通过（MVCC→多版本并发控制 alias 写入验证）

---

## ❌ 未完成

### 数据
- [ ] 1064 题数据迁移（backfill_relations.py）
- [ ] knowledge_embeddings flush 异步化（当前未 flush，跨轮去重需等数据落盘）
- [ ] 向量数据全量入库（测试仅 10 条）

### 前端
- [ ] 模拟面试页面（"敬请期待"占位）
- [ ] 题库：点击标记"已掌握/未掌握"按钮
- [ ] 题库：按用户水平/偏好排序
- [ ] 用户中心：简历上传
- [ ] Chat 页面：消息历史 + streaming 输出

### 架构
- [ ] Phase 3 解耦（PUBLIC_PATHS 硬编码、N+1 查询、sync LLM）
- [ ] tracer.py → OpenTelemetry/LangFuse 导出（AgentTrace/PromptCallLog 已落 PG，但未接外部平台）
- [ ] RabbitMQ 组件已完成但未接入（`src/common/rabbitmq.py` 无人引用）
- [ ] HTTPS/SSL（无域名）

### CI/CD
- [ ] GitHub Actions 自动化部署
- [ ] deploy.sh 完善（aerich 迁移在容器内有已知问题）
- [ ] Dockerfile 重建流程（当前依赖 docker cp 手工热更文件）

---

## 💡 优化建议

### 性能
| # | 建议 | 原因 |
|---|------|------|
| 1 | `generate_schemas=True` → aerich 迁移 | Tortoise 的 generate_schemas 不处理已有表的字段变更，本地/服务器 schema 漂移 |
| 2 | 开发环境挂载 volumes | 避免每次 docker cp → restart 丢失文件，改一行代码秒生效 |
| 3 | Milvus 搜索阈值 rrf_score 加下限过滤 | 当前 10 条向量时噪声查询也返回 5 条结果 |
| 4 | gen_topic_content 的字段长度约束收紧 | one_liner/core_summary/detailed_explanation 偶超字数，prompt 可加强约束 |

### 代码
| # | 建议 | 原因 |
|---|------|------|
| 5 | 清理 `src/agent/` 残留 v2 代码 | 已从 main.py 移除，文件还在 |
| 6 | 清理 `src/skills/gen_skill.md`（旧版） | 已被 gen_topic_content + gen_topic_topology 替代 |
| 7 | 清理 `tests/full_pipeline_test.py` | 已被 30 行 api_test.py 替代，那个脚本嵌了太多业务逻辑 |
| 8 | `query_skill.md` 文件保留但实际未被 `query_db.py` 引用 | query_db.py 内嵌了 `_BASE_SKILL` 常量 |

### 测试
| # | 建议 | 原因 |
|---|------|------|
| 9 | PostgreSQL 数据清理用 SQL DELETE，不动 Milvus collection | 避免每轮测试重建 HNSW 索引（节约 3s） |
| 10 | 本地 DB 同步服务器 schema | 本地 PG 仍缺 `one_liner` 等字段，本地测试无法运行 |
| 11 | 单测覆盖率 | 当前只有知识点去重 + API 调用两个单测，generate/normalize/search 等能力无覆盖 |

### 安全
| # | 建议 | 原因 |
|---|------|------|
| 12 | promt 中的 `hint` → `answer_hint` 已改 skill，但 gen_topic_content.md 示例 JSON 的 key 仍需核实 | 防止字段名不匹配导致写入静默失败 |
| 13 | `_BASE_SKILL` 在 query_db.py 中硬编码了 DB schema | 与 schema_manager 的 Milvus 检索逻辑重复，应统一 |

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
