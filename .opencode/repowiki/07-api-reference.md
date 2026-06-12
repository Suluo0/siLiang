# API 参考

> **生成时间**：2026-06-12 00:06:53  
> **基于提交**：168f526（main）  
> **覆盖模块**：面试题生成模块、用户与认证模块

---

## API 概览

- 端点总数：20+
- 认证方式：JWT Bearer Token（HS256）
- 基础路径：`http://localhost:8000`

## API 分组

```mermaid
graph LR
  subgraph 公开 API
    A[/ping]
    B[/api/auth/*]
    C[/api/v1/topic/tags]
    D[/api/v1/topic/positions]
  end
  subgraph 需认证 API
    E[/api/v1/topic/list]
    F[/api/v1/topic/{id}]
    G[/api/v3/topic/generate]
    H[/api/auth/me]
  end
```

## 端点清单

### 面试题相关

| 方法 | 路径 | 所属模块 | 认证 | 说明 |
|------|------|----------|------|------|
| `POST` | `/api/v3/topic/generate` | 面试题生成 | 是 | Agent Loop 生成面试题。Body: `{user_input: str}` (2-500 chars) |
| `GET` | `/api/v1/topic/list` | 面试题生成 | 否 | 分页查询题库。Query: `keyword`, `tag`, `limit`(20), `offset`(0) |
| `GET` | `/api/v1/topic/{topic_id}` | 面试题生成 | 否 | 题目详情（配额耗尽时截断内容） |
| `GET` | `/api/v1/topic/tags` | 面试题生成 | 否 | 获取所有标签（5 分钟缓存） |
| `POST` | `/api/v1/topic/{topic_id}/status` | 面试题生成 | 是 | 标记题目状态。Body: `{status: "mastered"|"learning"}` |
| `GET` | `/api/v1/topic/dashboard/stats` | 面试题生成 | 否 | Dashboard 统计数据 |
| `GET` | `/api/v1/topic/positions` | 面试题生成 | 否 | 获取目标岗位列表 |

### 认证相关

| 方法 | 路径 | 所属模块 | 认证 | 说明 |
|------|------|----------|------|------|
| `POST` | `/api/auth/register` | 用户认证 | 否 | 注册。Body: `{username, password, email, captcha_id, captcha_code, email_code}` |
| `POST` | `/api/auth/login` | 用户认证 | 否 | 登录。Body: `{username, password, captcha_id, captcha_code}` |
| `POST` | `/api/auth/refresh` | 用户认证 | 否 | 刷新 Token。Body: `{refresh_token}` |
| `GET` | `/api/auth/captcha` | 用户认证 | 否 | 获取图形验证码。返回: `{captcha_id, captcha_text}` |
| `POST` | `/api/auth/send-code` | 用户认证 | 否 | 发送邮箱验证码。Body: `{email, captcha_id, captcha_code}` |
| `GET` | `/api/auth/me` | 用户认证 | 是 | 获取当前用户信息（含配额） |
| `POST` | `/api/auth/change-password` | 用户认证 | 是 | 修改密码。Body: `{old_password, new_password}` |
| `POST` | `/api/auth/preferences` | 用户认证 | 是 | 更新学习偏好。Body: `{target_position, learning_preference, experience_level, today_target}` |

### 其他

| 方法 | 路径 | 所属模块 | 认证 | 说明 |
|------|------|----------|------|------|
| `GET` | `/ping` | 系统 | 否 | 健康检查。返回: `{status:"ok", timestamp, service}` |
| `GET` | `/` | 系统 | 否 | 服务信息。返回: `{service, status, capabilities}` |
| `GET` | `/docs` | 系统 | 否 | FastAPI Swagger 文档 |

## 请求/响应格式

### 通用请求头

| 头名称 | 说明 | 必填 |
|--------|------|------|
| `Authorization` | `Bearer {access_token}` | 认证端点必填 |
| `Content-Type` | `application/json` | 是 |

### Agent 生成响应（v3）

```json
{
  "success": true,
  "source": "recall",
  "topic_id": "uuid",
  "topic_name": "HashMap底层实现",
  "domain": "数据结构",
  "confidence": 0.91,
  "trace_id": "abc-123",
  "message": "..."
}
```

- `source`：`"recall"`（召回命中）/ `"generated"`（兜底生成）/ `"rejected"`（输入不合法）
- `confidence`：0.0-1.0 置信度

### 题目详情响应（v1）

```json
{
  "id": "uuid",
  "topic": "HashMap底层实现",
  "domain": "数据结构",
  "category": "哈希表",
  "difficulty": 3,
  "keywords": ["HashMap", "哈希表", "散列表"],
  "core_summary": "...",
  "detailed_explanation": "...",
  "code_example": "...",
  "prerequisites": [{"content": "...", "sort_order": 1}],
  "core_concepts": [...],
  "similar_questions": [{"question": "...", "answer_hint": "..."}],
  ...
}
```

**配额锁定响应**（配额耗尽用户）：
```json
{
  "locked": true,
  "locked_sections": ["detailed_explanation", "code_example", "traps", "bonuses"],
  "detailed_explanation": "HashMap 是 Java 中基于哈希表实现的 Map 接口...(前200字)..."
}
```

### 错误码

| 错误码 | HTTP 状态码 | 说明 |
|--------|-------------|------|
| `INPUT_TOO_SHORT` | 422 | 输入少于 2 字符 |
| `INPUT_TOO_LONG` | 422 | 输入超过 500 字符 |
| `LLM_ERROR` | 502 | LLM API 调用失败 |
| `AGENT_EXHAUSTED` | 500 | Agent 预算耗尽 |
| `DUPLICATE_TOPIC` | 409 | 面试题已存在 |
| `QUOTA_EXHAUSTED` | 403 | 配额用尽 |

**语义错误码**（`src/common/semantic_error.py`）：
| 错误码 | 说明 |
|--------|------|
| `SEM_1001` | 输入为空 |
| `SEM_1002` | 输入过长 |
| `SEM_2001` | 输入语义模糊 |
| `SEM_2002` | 输入存在冲突 |
| `SEM_3001` | 不支持的语言 |
| `SEM_5001` | 服务内部错误 |
| `SEM_5002` | 服务超时 |
