# Topic API 使用文档

## 概述

完整链路：**外部API → 语义转换 → Skill生成 → 落库**

项目已实现从用户输入到数据落库的完整流程，支持通过 FastAPI 端点调用。

---

## API 端点

### 1. 生成面试题（完整链路）

**端点**: `POST /api/v1/topic/generate`

**功能**: 接收用户输入，执行语义转换、调用 LLM + Skill 生成面试题、落库保存

**请求体**:
```json
{
  "user_input": "HashMap底层实现",
  "save_response": true
}
```

**参数说明**:
- `user_input` (必填): 用户原始输入，如 "HashMap底层实现"
- `save_response` (可选): 是否保存 LLM 响应到文件，默认 true

**响应示例（成功）**:
```json
{
  "success": true,
  "message": "Topic 创建成功",
  "topic": {
    "topic_id": "3be453ee-ee53-41b6-8a71-8cd84a26c2bb",
    "topic_name": "HashMap底层原理与面试深度解析",
    "domain": "Java",
    "difficulty": 3,
    "alias": ["HashMap实现原理", "哈希表原理"],
    "tags": ["高频", "必问", "原理", "实战"],
    "keywords": ["HashMap", "哈希表", "数组", "链表", "红黑树"]
  },
  "semantic_trans": {
    "standardized_output": "HashMap 的底层实现",
    "confidence": 0.99
  }
}
```

**响应示例（失败）**:
```json
{
  "success": false,
  "message": "语义转换失败",
  "error_code": "SEM_1001",
  "error_detail": "输入过于模糊"
}
```

---

### 2. 健康检查

**端点**: `GET /api/v1/topic/health`

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2026-04-28T12:34:56.789Z",
  "version": "1.0.0"
}
```

---

### 3. 测试语义转换（不生成不落库）

**端点**: `GET /api/v1/topic/test-semantic?user_input=HashMap底层实现`

**功能**: 仅测试语义转换功能，不调用 LLM，不落库

**响应示例**:
```json
{
  "success": true,
  "standardized_output": "HashMap 的底层实现",
  "confidence": 0.99
}
```

---

## 完整链路说明

### 流程图

```
用户输入
   ↓
[1] 语义转换 (semantic_convert)
   ↓
标准化输出
   ↓
[2] LLM + Skill 生成 (generate_topic)
   ↓
JSON 数据
   ↓
[3] 落库保存 (save_topic)
   ↓
Topic ID
```

### 各阶段说明

#### 1. 语义转换 (Semantic Conversion)
- **输入**: 用户原始输入，如 "HashMap底层实现"
- **处理**: 通过语义规则库标准化用户输入
- **输出**: 标准化描述，如 "HashMap 的底层实现"
- **置信度**: 0.0-1.0，表示转换的准确性

#### 2. Skill 生成 (LLM + Skill)
- **输入**: 标准化输出
- **处理**: 调用 LLM，使用 `generateByTopic` skill 生成完整面试题数据
- **输出**: JSON 格式的面试题数据，包含：
  - topic (主表): 题目信息、难度、标签、关键词等
  - prerequisites (前置知识): 4条
  - core_concepts (核心概念): 5条
  - derivatives (衍生知识): 3条
  - extensions (扩展知识): 3条
  - evaluation_anchors (评估锚点): 3条 (入门/掌握/精通)
  - similar_questions (相似问题): 3条
  - advanced_questions (进阶问题): 2条
  - references (参考资料): 3条

#### 3. 落库保存 (Database Persistence)
- **输入**: JSON 数据
- **处理**: 
  - 防重检查：检查题目是否已存在
  - 事务保证：所有操作在事务中执行，失败自动回滚
  - 批量插入：主表 + 8个关联表一次性插入
- **输出**: Topic 实例，包含 topic_id

---

## 启动服务

### 1. 安装依赖
```bash
cd /Users/xunsu/PycharmProjects/PythonProject/TopicSystem
poetry install
```

### 2. 配置环境变量
编辑 `.env` 文件：
```bash
# 数据库配置
DATABASE_URL="postgres://postgres:password@localhost:5432/topic"

# API 配置
API_SECRET="your-api-key"
API_ADDRESS="https://api.minimaxi.com/v1"
API_MODEL="MiniMax-M2.7"
```

### 3. 启动服务
```bash
source .venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后访问：
- API 文档: http://localhost:8000/docs
- Redoc 文档: http://localhost:8000/redoc

---

## 测试示例

### 使用 curl 测试

```bash
# 1. 健康检查
curl http://localhost:8000/api/v1/topic/health

# 2. 仅测试语义转换
curl "http://localhost:8000/api/v1/topic/test-semantic?user_input=HashMap底层实现"

# 3. 完整链路测试
curl -X POST http://localhost:8000/api/v1/topic/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Python装饰器原理",
    "save_response": true
  }'
```

### 使用 Python requests 测试

```python
import requests

# 完整链路请求
response = requests.post(
    "http://localhost:8000/api/v1/topic/generate",
    json={
        "user_input": "HashMap底层实现",
        "save_response": True
    }
)

result = response.json()
print(f"成功: {result['success']}")
print(f"消息: {result['message']}")

if result['success']:
    print(f"Topic ID: {result['topic']['topic_id']}")
    print(f"Topic 名称: {result['topic']['topic_name']}")
```

---

## 运行测试

### 单元测试
```bash
# 测试语义转换 + JSON解析 + 落库
pytest tests/test_topic_save.py -v

# 测试完整链路（使用已有JSON）
python tests/test_api_with_json.py
```

### 集成测试
```bash
# 测试完整 API 链路（需要 LLM 服务可用）
python tests/test_topic_api_flow.py
```

---

## 关键组件

### 1. TopicService (`src/service/topic_service.py`)
- `semantic_convert()`: 语义转换函数
- `generate_topic()`: LLM + Skill 生成
- `save_topic()`: 落库保存
- `get_topic_flow()`: 完整流程（异步）

### 2. TopicAPI (`src/api/topic_api.py`)
- `generate_topic()`: FastAPI 端点实现
- 完整的请求/响应模型定义
- 错误处理和日志记录

### 3. 数据模型
- `Topic`: 主表（一表一model原则）
- 8个关联表：prerequisites, core_concepts, derivatives, extensions, evaluation_anchors, similar_questions, advanced_questions, references

---

## 常见问题

### Q1: 如何查看生成的 JSON 数据？
A: 生成的 JSON 数据保存在 `src/service/json_output/` 目录下，文件名格式：`面试题_{topic}_{timestamp}.json`

### Q2: 如何处理重复的题目？
A: 系统会自动检查题目是否已存在，如果存在会返回错误：`"Topic '{name}' already exists"`

### Q3: LLM 调用失败怎么办？
A: 检查：
1. `.env` 中的 `API_SECRET` 和 `API_ADDRESS` 是否正确
2. 网络连接是否正常
3. API 配额是否充足

### Q4: 如何自定义 Skill？
A: 编辑 `skill/generateByTopic/skill_v2.md` 文件，修改生成规则和模板

---

## 技术栈

- **Web 框架**: FastAPI
- **ORM**: Tortoise-ORM
- **数据库**: PostgreSQL
- **LLM**: LangChain + ChatOpenAI
- **数据验证**: Pydantic v2
- **测试**: pytest + pytest-asyncio

---

## 维护者

- 作者: xunsu
- 项目路径: `/Users/xunsu/PycharmProjects/PythonProject/TopicSystem`
- 更新时间: 2026-04-28