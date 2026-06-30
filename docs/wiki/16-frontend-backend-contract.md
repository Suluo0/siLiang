# 前后端交互契约（路由 → API → 数据库）

> **生成时间**：2026-06-21
> **用途**：还原"前端路由/页面 → 调用哪个 API → 落到哪张数据库表"的端到端映射。
> 做前端任务时先查本表定位接口与字段，避免来回 read 前端 api.js + 后端 api.py。
> **维护**：本文档随相关页面/接口/表改动做**最小增量更新**（只改受影响行），不全量重写。

---

## 0. 基础约定

| 项 | 说明 |
|---|---|
| 前端请求基址 | `/api`（`api/request.js` 的 axios baseURL；nginx 把 `/api/` 反代到 `127.0.0.1:8000`） |
| 后端路由前缀 | `topic→/api/topic`、`auth→/api/auth`、`menu→/api/menu`、`interview→/api/interview`、healthcheck 无前缀 |
| 鉴权 | JWT，`localStorage.token`；中间件 `src/middleware/auth.py`，公开路径白名单在 `src/auth/deps.py:PUBLIC_PATHS` |
| 公开接口（游客可访问） | `/api/topic/tags`、`/api/topic/positions`、`/api/auth/{register,login,refresh,captcha,send-code}`、`/terms`、`/privacy` |

---

## 1. 前端路由表（`router/index.js`）

| 路径 | name | 页面组件 | 权限 |
|---|---|---|---|
| `/login` | Login | `Auth/Login.vue` | 游客 |
| `/dashboard` | Dashboard | `Dashboard/index.vue` | 登录 |
| `/topic/library` | TopicLibrary | `Topic/topic_list.vue` | 游客 |
| `/topic/practice` | TopicPractice | `Topic/Practice.vue` | 登录 |
| `/topic/detail/:id` | TopicDetail | `Topic/topic_detail.vue` | 游客 |
| `/user/list` | UserList | `User/List.vue` | 管理员 |
| `/user/level` | UserLevel | `User/Level.vue` | 管理员 |
| `/user-center` | UserCenter | `User/Center.vue` | 登录 |
| `/skill/generate` | SkillGenerate | `Skill/Generate.vue` | 登录 |
| `/system/menu` | SystemMenu | `System/Menu.vue` | 管理员 |
| `/system/permission` | SystemPermission | `System/Permission.vue` | 管理员 |
| `/chat` | Chat | `Chat/index.vue` | 登录 |
| `/interview` | Interview | `Interview/index.vue` | 登录 |
| `/privacy` `/terms` | Privacy/Terms | `Legal/*.vue` | 游客 |

---

## 2. 交互契约总表（前端调用方 → API → DB 表）

### 2.1 题库 / 题目（`/api/topic`，后端 `api/topic_api.py`）

| 前端调用方 | API | 请求 | 响应结构 | DB 表 |
|---|---|---|---|---|
| `api/topic.js` `getTopicList()`<br>题库页 `topic_list.vue` + 刷题页 `Practice.vue` | `GET /topic/list` | `keyword, tag, limit`（query） | `{items[], total}`，item 含 `id/topic/domain/difficulty/tags` + `user_status`（mastered/learning/null，按当前登录用户实时注入，**不进缓存**避免串用户） | `topic` + `user_topic_status` |
| `api/topic.js` `getTopicTags()`<br>题库页标签栏 | `GET /topic/tags` | 无 | `{tags: string[]}` **扁平数组，无分类**（分类在前端 `topic_list.vue` 的 `DIM_DEF` 做） | `topic.tags`（JSON 列聚合，缓存 300s） |
| `api/topic.js` `getTopicDetail()`<br>详情页 `topic_detail.vue` | `GET /topic/{topic_id}` | path id | 题目全字段 + 关联子表 | `topic` + 8 子表（`topic_core_concept`/`derivative`/`prerequisite`/`extension`/`reference`/`advanced_question`/`similar_question`/`evaluation_anchor`） |
| `topic_detail.vue` + 刷题页 `MasteryPanel.vue`（标记掌握/状态，旁路） | `POST /topic/{topic_id}/status` | body `{status}` (mastered/learning) | 操作结果 | `user_topic_status` |
| `StatsSection.vue`（首页统计卡） | `GET /topic/dashboard/stats` | 无 | `{total_topics, mastered, learning, today_target, preferences_filled, authenticated}` | `topic` + `user_topic_status` + `user` |
| `PreferencesModal.vue` / `User/Center.vue`（岗位下拉） | `GET /topic/positions` | 无 | `{items:[{id,name,category}]}` | `job_position` ⚠️（反模式空专表，字典治理候选） |
| `Chat/index.vue`（AI 出题，fetch 流式） | `POST /topic/generate` | `{user_input}` | `GenerateResponse`（题目 + 衍生） | `topic` 系列（Agent 双写 + `outbox`） |
| 详情页 + 刷题页 `MasteryPanel.vue`（掌握度自测，主路径） | `POST /topic/{topic_id}/mastery-check` | `{answer}` (≥10字) | 五维评分 `{total, mastered, scores{keypoint/keyword/structure/length/coherence}, feedback}` | `mastery_attempt` + `user_topic_status` |
| 刷题页 `MasteryPanel.vue`（历史自查记录） | `GET /topic/{topic_id}/attempts` | path id（需登录，未登录 401） | `{attempts[]{attempt_number, answer_text, scores{}, total, is_mastered, created_at}, user_status, mastery_score, mastery_attempts}` 倒序，≤50 条 | `mastery_attempt` + `user_topic_status` |

### 2.2 认证 / 用户（`/api/auth`，后端 `auth/api.py`）

| 前端调用方 | API | 请求 | 响应 | DB 表 |
|---|---|---|---|---|
| `Login.vue` | `GET /auth/captcha` | 无 | 图形验证码 | `captcha` |
| `Login.vue` | `POST /auth/login` | `{username,password,captcha...}` | `TokenResponse`（access+refresh） | `user` |
| `Login.vue` | `POST /auth/send-code` | `{email}` | 发邮件验证码 | `captcha`（+ SMTP，`utils/mail.py`） |
| `Login.vue` | `POST /auth/register` | `{username,email,password,code}` | `TokenResponse` | `user` |
| `api/request.js`（401 自动刷新） | `POST /auth/refresh` | `{refresh_token}` | `TokenResponse` | `user` |
| `User/Center.vue` | `GET /auth/me` | 无 | `UserResponse` | `user` |
| `User/Center.vue` | `POST /auth/change-password` | `{old,new}` | 结果 | `user` |
| `User/Center.vue` / `PreferencesModal.vue` | `POST /auth/preferences` | 偏好（岗位/标签等） | 结果 | `user_profile`（+ `user_quota` 相关） |

### 2.3 菜单（`/api/menu`，后端 `api/menu_api.py`）

| 前端调用方 | API | 请求 | 响应 | DB 表 |
|---|---|---|---|---|
| `api/menu.js` `getMenuList()` | `GET /menu/list` | 无 | `List[MenuItem]` | `menu` |
| `api/menu.js` `getMenuTree()`<br>`System/Menu.vue` | `GET /menu/tree` | 无 | `List[MenuTreeItem]`（树） | `menu` |

### 2.4 模拟面试（`/api/interview`，后端 `api/interview_api.py`）

| 前端调用方 | API | 请求 | 响应 | DB 表 |
|---|---|---|---|---|
| `Interview/index.vue`（fetch） | `POST /interview/start` | `StartRequest` | `StartResponse`（room+首题） | `interview_room` + `interview_persona` |
| `Interview/index.vue`（fetch） | `POST /interview/answer` | `AnswerRequest` | `AnswerResponse`（评分+下一题） | `interview_round` |
| `Interview/index.vue`（fetch） | `GET /interview/{room_id}/summary` | path room_id | `SummaryResponse` | `interview_summary` + `interview_round` |
| （面试官风格选择） | `GET /interview/personas` | 无 | persona 列表 | `interview_persona` |

### 2.5 健康检查

| 前端调用方 | API | 响应 | 备注 |
|---|---|---|---|
| 运维/nginx | `GET /ping` | `PingResponse` | 无前缀，部署冒烟用 |

---

## 3. 数据库表全景（30 张）

> 完整 ER 见 [14-database.md](14-database.md)。本表只标"被前端链路直接/间接命中"的表。

| 表 | 被哪些 API 命中 | 说明 |
|---|---|---|
| `topic` | list/tags/detail/stats/generate | 题目主表，`tags` 为 JSON 列 |
| `topic_*`（8 子表） | detail/generate | core_concept/derivative/prerequisite/extension/reference/advanced_question/similar_question/evaluation_anchor |
| `user` | auth 全套 / stats | 用户主表 |
| `user_profile` | preferences | 用户偏好 |
| `user_quota` | preferences/login | 配额 |
| `user_topic_status` | status/stats/mastery-check | 用户-题目掌握状态 |
| `user_topic_progress` | （进度统计） | 学习进度 |
| `mastery_attempt` | mastery-check | 五维评分记录 |
| `captcha` | captcha/send-code/register | 验证码 |
| `menu` | menu/list、menu/tree | 菜单 |
| `job_position` ⚠️ | positions | 岗位（空专表，字典治理候选） |
| `interview_room/round/summary/persona` | interview 全套 | 面试子系统 |
| `outbox` | generate（双写补偿） | 事务发件箱 |
| `knowledge_dict/alias` | （Agent 内部） | 知识词典 |
| `prompt_call_log/agent_trace` | （Agent 内部） | LLM 调用追踪 |

---

## 4. 维护说明（最小增量更新）

改动落地时，**只更新本文档受影响的行**：

- **改了某页面调用的接口** → 更新 §2 对应行的"请求/响应"列
- **新增/删除路由** → 更新 §1 路由表 + §2 对应分区
- **新增/删除 API 端点** → 更新 §2 对应分区
- **改了某表结构且影响接口返回** → 更新 §2 响应列 + §3 表说明

不因单点改动而全量重写。本文档与 `wiki-state.json` 一同纳入增量算法。
