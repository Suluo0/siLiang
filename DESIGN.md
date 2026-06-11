# TopicSystem v2 — 技术设计文档

> 基于 LangGraph Agent Loop 的 AI 面试题生成与召回系统

---

## 一、项目定位

将 v1 的线性流水线（API → Service → LLM → DB）重构为 **Agent 自主编排** 架构。Agent 内部通过状态机驱动 6 个节点协作，根据召回质量自动分支（命中直接返回 / 未命中兜底生成），所有操作通过 OpenTelemetry + LangFuse 全链路追踪。

---

## 二、技术选型

| 层 | 选型 | 版本 | 理由 |
|----|------|------|------|
| Agent 框架 | LangGraph | >= 0.2 | Python 侧等价于 langchain4j，原生 StateGraph + 条件边 |
| LLM 适配 | LangChain ChatOpenAI | >= 0.3 | 统一接口，兼容 MiniMax / DeepSeek / OpenAI |
| Embedding | BAAI/bge-large-zh-v1.5 | latest | C-MTEB 中文榜首，1024 维，MIT 协议 |
| 向量数据库 | Milvus | 2.4 standalone | HNSW 索引，支持混合检索，Docker 单节点部署 |
| 关系数据库 | PostgreSQL + Tortoise ORM | 16 + 0.24 | 复用 v1 基础设施，Aerich 管理迁移 |
| 消息补偿 | Outbox Pattern (pg) | — | 保证 Milvus 写入最终一致性，零额外中间件 |
| 链路追踪 | OpenTelemetry + LangFuse | latest | OTel 行业标准，LangFuse 专为 LLM 链路优化 |
| Web 框架 | FastAPI | >= 0.115 | 异步原生，SSE 流式支持 |
| 依赖管理 | Poetry | latest | Python 依赖锁定与虚拟环境管理 |

---

## 三、整体架构

```
                          POST /api/v2/topic/generate
                                    │
                          ┌─────────▼─────────┐
                          │  FastAPI Endpoint  │
                          │  (topic_api.py)    │
                          └─────────┬─────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │        Agent Graph             │
                    │     (agent/graph.py)           │
                    │                                │
                    │  ┌─────────────────────────┐  │
                    │  │     State Machine        │  │
                    │  │                          │  │
                    │  │  IDLE                    │  │
                    │  │   │                      │  │
                    │  │   ▼                      │  │
                    │  │  NORMALIZE ───(LLM)──►   │  │
                    │  │   │                      │  │
                    │  │   ▼                      │  │
                    │  │  RECALL ──(Embedding)─►  │  │
                    │  │   │         (Milvus)     │  │
                    │  │   ▼                      │  │
                    │  │  VERIFY ─(多维度校验)►    │  │
                    │  │   │           │          │  │
                    │  │   │ HIT       │ MISS     │  │
                    │  │   ▼           ▼          │  │
                    │  │  RESPOND   GENERATE      │  │
                    │  │              │           │  │
                    │  │              ▼           │  │
                    │  │           DUAL_WRITE     │  │
                    │  │           (PG+Milvus)    │  │
                    │  │              │           │  │
                    │  │              ▼           │  │
                    │  │           RESPOND        │  │
                    │  │              │           │  │
                    │  │              ▼           │  │
                    │  │            DONE          │  │
                    │  └─────────────────────────┘  │
                    └───────────────────────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │   OpenTelemetry   │
                          │   + LangFuse      │
                          │   (链路追踪)       │
                          └───────────────────┘
```

---

## 四、状态机设计

### 4.1 状态定义

| 状态 | 含义 | 触发条件 |
|------|------|----------|
| `IDLE` | 初始状态 | 用户请求进入 |
| `NORMALIZING` | 正在语义归一化 | Agent 开始处理 |
| `NORMALIZED` | 归一化完成 | LLM 返回有效结构化结果 |
| `RECALLING` | 正在向量召回 | 归一化完成 |
| `RECALLED` | 召回完成 | Milvus 返回 top-K 结果 |
| `VERIFYING` | 正在校验召回质量 | 召回结果就绪 |
| `VERIFIED_HIT` | 召回命中，质量合格 | 加权分 ≥ 0.75 |
| `VERIFIED_MISS` | 召回失败，需兜底生成 | 加权分 < 0.75 |
| `GENERATING` | Gen_skill 正在生成 | 校验结果为 MISS |
| `GENERATED` | LLM 生成完成 | 结构化 JSON 解析成功 |
| `DUAL_WRITING` | 正在双写 PG + Milvus | 生成完成 |
| `WRITTEN` | 双写完成 | PG + Milvus 均写入成功 |
| `RESPONDING` | 正在组装响应 | HIT 或 WRITTEN |
| `DONE` | 请求处理完成 | 响应已返回 |
| `ERROR` | 异常终止 | 任意节点异常 |

### 4.2 状态转换图

```
IDLE ──► NORMALIZING ──► NORMALIZED ──► RECALLING ──► RECALLED ──► VERIFYING
                                                                         │
                                                          ┌──────────────┼──────────────┐
                                                          │ HIT                         │ MISS
                                                          ▼                             ▼
                                                    VERIFIED_HIT                 VERIFIED_MISS
                                                          │                             │
                                                          │                             ▼
                                                          │                       GENERATING
                                                          │                             │
                                                          │                             ▼
                                                          │                       GENERATED
                                                          │                             │
                                                          │                             ▼
                                                          │                       DUAL_WRITING
                                                          │                             │
                                                          │                             ▼
                                                          │                        WRITTEN
                                                          │                             │
                                                          └─────────┬───────────────────┘
                                                                    ▼
                                                               RESPONDING
                                                                    │
                                                                    ▼
                                                                  DONE

任意状态 ──(异常)──► ERROR
```

### 4.3 LangGraph 条件边逻辑

```python
# agent/graph.py
workflow = StateGraph(AgentState)

# 顺序边
workflow.add_edge("NORMALIZE", "RECALL")
workflow.add_edge("RECALL", "VERIFY")
workflow.add_edge("GENERATE", "DUAL_WRITE")
workflow.add_edge("DUAL_WRITE", "RESPOND")

# 条件边: VERIFY 节点根据校验结果分流
workflow.add_conditional_edges(
    "VERIFY",
    decide_after_verify,             # 决策函数
    {
        "hit": "RESPOND",            # 命中 → 直接响应
        "miss": "GENERATE",          # 未命中 → 兜底生成
    }
)

def decide_after_verify(state: AgentState) -> str:
    return "hit" if state["verdict"] == "HIT" else "miss"
```

---

## 五、节点详细设计

### 5.1 NORMALIZE — 语义归一化

**职责**：将用户自由文本转化为结构化查询对象。

**能力边界**（显式定义的 contract）：

```
✅ 能力范围:
  - 中英文技术术语统一        HashMap → 哈希表
  - 缩写展开                    IoC → 控制反转, AOP → 面向切面编程
  - 口语化 → 标准术语           "java怎么实现锁" → "Java 锁机制"
  - 领域/子领域分类             数据库 → MySQL → 事务隔离级别
  - 提取核心概念 + 关键词列表   "Python 装饰器原理及应用" →
                               core_concept="Python装饰器",
                               keywords=["装饰器","闭包","functools","AOP"]

❌ 边界外（显式拒绝）:
  - 多跳推理                   "会Python装饰器的人怎么学Java注解"
                                → 返回 boundary_check=OUT_OF_SCOPE
  - 非技术问题                 "今天天气怎么样"
                                → 返回 boundary_check=UNSUPPORTED_DOMAIN
  - 代码调试请求               "这段代码为什么报错 NullPointerException"
                                → 返回 boundary_check=UNSUPPORTED_INPUT_TYPE
  - 纯主观评价                 "Python 是最好的语言吗"
                                → 降级处理, confidence < 0.7, 返回原文

📐 置信度规则:
  - ≥ 0.85: 高置信度，直接使用
  - 0.70-0.85: 中等，可用但标记
  - < 0.70: 低置信度，降级为原文字面匹配
```

**输入**：`str` — 用户原始文本

**输出**：`NormalizedQuery`

```python
class NormalizedQuery(BaseModel):
    core_concept: str           # 核心技术概念，如 "哈希表底层实现"
    domain: str                 # 一级领域，如 "数据结构"
    subdomain: str | None       # 二级子领域，如 "哈希表"
    keywords: list[str]         # 关键词列表 2-5个
    language: str               # zh / en / mixed
    confidence: float           # 归一化置信度 0-1
    boundary_check: str         # IN_SCOPE / OUT_OF_SCOPE / UNSUPPORTED_DOMAIN / UNSUPPORTED_INPUT_TYPE
```

**实现细节**：

| 步骤 | 操作 | 工具 |
|------|------|------|
| 1 | 预处理：移除无意义语气词，标点规范化 | Python `re` |
| 2 | LLM 调用，JSON Schema 约束输出 | LangChain `with_structured_output(NormalizedQuery)` |
| 3 | 置信度检查 | 代码判断 `confidence < 0.7` 分支 |
| 4 | 边界检查 | 代码判断 `boundary_check` 字段 |
| 5 | 写入状态 | 更新 `AgentState.normalized` |

**LLM 配置**：
- 模型：MiniMax M2.7 / DeepSeek-V3
- Temperature: 0.1（归一化需要确定性输出）
- Max Tokens: 512
- JSON Mode: ON

**Skill Prompt 路径**：`src/skills/normalize_skill.md`

---

### 5.2 RECALL — 向量召回 + 多重校验

**职责**：从 Milvus 向量数据库中检索与归一化概念最匹配的已知面试题，**在召回阶段内置 5 层防呆校验 + 双分数机制**，不依赖下游二次确认。

**设计原则**：

> 向量相似度 ≠ 语义相关性。Embedding 模型可能将"线程池"和"数据库连接池"判为高相似（都含"池"），因此不能仅凭 cosine 分数做决策。必须引入 **自然语言语义校验** 作为第二道防线，任何单一分数不可信。

---

#### 5.2.1 防呆层级总览

```
输入: NormalizedQuery  ──────────────────────────────────────────► 输出: RecallResult[] + verdict

  ┌─────────────────────────────────────────────────────────────────────────┐
  │                                                                         │
  │  Layer 0 │ 输入门      │ 归一化结果是否合法？   │ 不合法 → 直接 MISS    │
  │  Layer 1 │ 向量质量门  │ Embedding 是否有效？   │ 无效   → ERROR        │
  │  Layer 2 │ 混合检索    │ Dense + Sparse 双路    │ 均空   → 直接 MISS    │
  │  Layer 3 │ ★ 双分数校验│ Score A + Score B      │ 任一不达标 → 淘汰     │
  │  Layer 4 │ 交叉验证门  │ Dense vs Sparse 互检   │ 分歧   → 降置信度     │
  │  Layer 5 │ 出口质量门  │ 最优候选是否过关？     │ 不过关 → MISS         │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘
```

---

#### 5.2.2 Layer 0 — 输入门（Input Gate）

**防的是**：归一化节点输出了垃圾、空串、超低置信度结果，Embedding 搜索必然产生噪音。

| 检查项 | 条件 | 不通过动作 |
|--------|------|------------|
| 空值检查 | `core_concept` 为空或纯空白 | 立即返回 MISS，跳过全部后续搜索 |
| 长度检查 | `len(core_concept) < 2` | 立即返回 MISS |
| 置信度下限 | `normalized.confidence < 0.7` | 立即返回 MISS，置信度过低说明归一化本身不可信 |
| 边界标记 | `boundary_check != "IN_SCOPE"` | 立即返回 MISS，超出技术面试题范围 |

```python
def input_gate(normalized: NormalizedQuery) -> GateResult:
    if not normalized.core_concept or not normalized.core_concept.strip():
        return GateResult(pass_=False, reason="EMPTY_INPUT", skip_to="MISS")
    if len(normalized.core_concept.strip()) < 2:
        return GateResult(pass_=False, reason="TOO_SHORT", skip_to="MISS")
    if normalized.confidence < 0.7:
        return GateResult(pass_=False, reason=f"LOW_CONFIDENCE({normalized.confidence:.2f})", skip_to="MISS")
    if normalized.boundary_check != "IN_SCOPE":
        return GateResult(pass_=False, reason=f"OUT_OF_SCOPE({normalized.boundary_check})", skip_to="MISS")
    return GateResult(pass_=True)
```

---

#### 5.2.3 Layer 1 — 向量质量门（Embedding Quality Gate）

**防的是**：Embedding 模型输出异常向量（NaN、Inf、维度错配、全零），这些向量在 Milvus 中仍会返回结果，但结果不可信。

| 检查项 | 条件 | 不通过动作 |
|--------|------|------------|
| NaN/Inf 检查 | `np.any(np.isnan(vector)) or np.any(np.isinf(vector))` | ERROR，模型推理异常 |
| 维度检查 | `len(vector) != 1024` | ERROR，模型配置错误 |
| 零向量检查 | `np.all(vector == 0)` | ERROR，模型未正常输出 |
| 自相似度检查 | `cosine(vector, vector) < 0.9999` | ERROR，浮点异常 |

```python
def embedding_quality_gate(vector: np.ndarray) -> GateResult:
    if np.any(np.isnan(vector)) or np.any(np.isinf(vector)):
        return GateResult(pass_=False, reason="EMBEDDING_NAN_INF", skip_to="ERROR")
    if vector.shape[-1] != 1024:
        return GateResult(pass_=False, reason=f"EMBEDDING_DIM_MISMATCH({vector.shape[-1]})", skip_to="ERROR")
    if np.all(vector == 0) or np.allclose(vector, 0):
        return GateResult(pass_=False, reason="EMBEDDING_ALL_ZERO", skip_to="ERROR")
    self_sim = cosine_similarity(vector, vector)
    if self_sim < 0.9999:
        return GateResult(pass_=False, reason=f"EMBEDDING_SELF_SIM({self_sim:.6f})", skip_to="ERROR")
    return GateResult(pass_=True)
```

---

#### 5.2.4 Layer 2 — 混合检索（Hybrid Search）

**防的是**：单路检索的盲区。Dense 可能遗漏精确关键词匹配（如"CAP 定理"被 embedding 误解为"C语言指针"），Sparse 可能遗漏同义表达（如"哈希表"搜不到"散列表"）。

| 检索路径 | 方法 | 召回数 | 目的 |
|----------|------|--------|------|
| Dense | `milvus.search(anns_field="embedding", metric_type="COSINE", limit=10)` | top-10 | 语义相似候选 |
| Sparse | `milvus.query(expr='keywords like "%{keyword}%"', limit=10)` | top-10 | 精确关键词匹配 |

> **拉取 top-10 而非 top-5**：下游 Layer 3/4/5 会做多轮过滤淘汰，首轮多拉一些候选避免被过早剪枝。

**融合算法 — RRF（Reciprocal Rank Fusion）**：

```python
def hybrid_search(query_vector, keywords, milvus_client) -> tuple[list, list]:
    # Dense 检索
    dense_hits = milvus_client.search(
        collection="topic_embeddings",
        data=[query_vector],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"ef": 128}},
        limit=10,
        output_fields=["topic_id", "core_concept", "domain", "keywords", "difficulty"]
    )[0]  # [0] 取第一个查询向量的结果

    # Sparse 检索（对每个关键词做 OR 检索）
    keyword_expr = " or ".join([f'keywords like "%{kw}%"' for kw in keywords])
    sparse_hits = milvus_client.query(expr=keyword_expr, limit=10,
                                       output_fields=["topic_id", "core_concept", "domain", "keywords"])

    # RRF 融合：对 Dense 和 Sparse 各自排名做倒数融合
    scores: dict[str, float] = {}
    for rank, hit in enumerate(dense_hits):
        scores[hit["topic_id"]] = scores.get(hit["topic_id"], 0) + 1.0 / (rank + 60)
    for rank, hit in enumerate(sparse_hits):
        scores[hit["topic_id"]] = scores.get(hit["topic_id"], 0) + 1.0 / (rank + 60)

    # 按 RRF 分数降序，保留 top-8（比最终需要的 5 多一些余地）
    merged = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:8]

    # 重建结果列表（保留原始 dense/sparse 标记用于 Layer 4 交叉验证）
    results = []
    for topic_id, rrf_score in merged:
        dense_match = next((h for h in dense_hits if h["topic_id"] == topic_id), None)
        sparse_match = next((h for h in sparse_hits if h["topic_id"] == topic_id), None)
        results.append(RecallCandidate(
            topic_id=topic_id,
            core_concept=dense_match["core_concept"] if dense_match else sparse_match["core_concept"],
            domain=dense_match["domain"] if dense_match else sparse_match["domain"],
            keywords=dense_match["keywords"] if dense_match else sparse_match["keywords"],
            rrf_score=rrf_score,
            from_dense=dense_match is not None,
            from_sparse=sparse_match is not None,
            dense_cosine=dense_match.get("score", 0) if dense_match and "score" in dense_match else None,
        ))

    return results, {"dense_count": len(dense_hits), "sparse_count": len(sparse_hits)}

# 防呆：双路均空 → 直接 MISS
if len(dense_hits) == 0 and len(sparse_hits) == 0:
    return GateResult(pass_=False, reason="HYBRID_SEARCH_EMPTY", skip_to="MISS")
```

---

#### 5.2.5 Layer 3 — 双分数校验（Dual Scoring） ★ 核心

**防的是**：向量相似度幻觉。Embedding 分数高不代表语义相关（典型案例：`"线程池"` 与 `"数据库连接池"` cosine 可达 0.85+，但根本不是同一个面试题）。必须用 **自然语言语义判断** 做第二眼确认。

**双分数定义**：

| 分数 | 来源 | 含义 | 阈值 |
|------|------|------|------|
| **Score A** — 向量余弦 | `cosine(query_embedding, candidate_embedding)` | Embedding 空间的几何相似度 | ≥ 0.75 |
| **Score B** — NL 语义匹配 | LLM 逐条判断候选是否真正回答查询意图 | 自然语言理解层面的语义相关性 | ≥ 0.70 |

> **为什么双阈值而非单阈值？**
> Score A 负责快速过滤明显不相关的（余弦 < 0.75 的直接淘汰，不再调用 LLM 浪费 token）。Score B 负责揪出 Score A 误判为高分的假阳性。双阈值是"粗筛 + 精判"的组合，既省成本又提升精度。

**Score B — NL 语义匹配实现**：

```
LLM System Prompt:
你是一个面试题匹配判定器。给定：
  - 用户查询: 归一化后的技术概念
  - 候选题目: 系统中已存储的面试题

请判断候选题目是否真正回答了用户查询。注意：
  - 只判断核心概念是否一致，不要求在细节层面的完全相同
  - 同一概念的不同表述视为匹配（例: "HashMap" = "哈希表" = "散列表"）
  - 不同概念即使共享关键词也不匹配（例: "线程池" ≠ "连接池"）
  - 部分重叠概念按重叠程度评分（例: "Java 并发" 与 "Java 线程池" 评 0.5）

返回 JSON: {"score": 0.0-1.0, "reasoning": "一句话解释"}

User Prompt:
用户查询: {normalized.core_concept}
查询领域: {normalized.domain}
候选题目: {candidate.core_concept}
候选领域: {candidate.domain}

请返回 JSON。
```

```python
async def dual_scoring(query: NormalizedQuery, candidates: list[RecallCandidate],
                       llm_client, embedding_model) -> list[RecallCandidate]:
    query_vector = embedding_model.encode(query.core_concept)
    scored_candidates = []

    for candidate in candidates:
        # ── Score A: 向量余弦 ──
        candidate_vector = embedding_model.encode(candidate.core_concept)
        score_a = cosine_similarity(query_vector, candidate_vector)

        # 快速过滤：Score A 不达标的直接淘汰，不调用 LLM
        if score_a < 0.75:
            candidate.passed = False
            candidate.reject_reason = f"SCORE_A_LOW({score_a:.3f})"
            candidate.score_a = score_a
            scored_candidates.append(candidate)
            continue

        candidate.score_a = score_a

        # ── Score B: NL 语义匹配（LLM 调用）──
        nl_result = await llm_client.invoke(
            system_prompt=NL_MATCH_SYSTEM_PROMPT,
            user_prompt=NL_MATCH_USER_PROMPT.format(
                query_concept=query.core_concept,
                query_domain=query.domain,
                candidate_concept=candidate.core_concept,
                candidate_domain=candidate.domain,
            ),
            response_format={"type": "json_object"},
            max_tokens=128,
            temperature=0.0,  # 判定任务需要确定性
        )
        parsed = json.loads(nl_result)
        score_b = float(parsed["score"])
        candidate.score_b = score_b
        candidate.nl_reasoning = parsed.get("reasoning", "")

        # ── 双阈值判定 ──
        if score_b >= 0.70:
            candidate.passed = True
            candidate.combined_score = 0.5 * score_a + 0.5 * score_b  # 等权融合
        else:
            candidate.passed = False
            candidate.reject_reason = f"SCORE_B_LOW({score_b:.3f})"
            candidate.combined_score = 0

        scored_candidates.append(candidate)

    return scored_candidates
```

**LLM 配置（Score B）**：
- 模型：DeepSeek-V3 / MiniMax-M2.7
- Temperature: **0.0**（判定任务，必须确定性输出）
- Max Tokens: 128
- JSON Mode: ON

---

#### 5.2.6 Layer 4 — 交叉验证门（Cross-Validation Gate）

**防的是**：Dense 和 Sparse 两条检索路径给出矛盾结论时，系统盲目信任其中一条。

| 检查项 | 条件 | 动作 |
|--------|------|------|
| Dense/Sparse 顶部分歧 | Dense top-1 ≠ Sparse top-1（经 Layer 3 过滤后） | 对受影响的候选 `combined_score *= 0.85` |
| 单路存活 | 只有 Dense 或只有 Sparse 返回有效候选 | 对候选 `combined_score *= 0.9`，并记录警告 |
| 两路一致 | Dense top-1 = Sparse top-1 且均通过 Layer 3 | `combined_score *= 1.05`（加分，上限 1.0） |

```python
def cross_validation_gate(candidates: list[RecallCandidate]) -> list[RecallCandidate]:
    passed = [c for c in candidates if c.passed]
    if not passed:
        return candidates

    dense_top = next((c for c in passed if c.from_dense), None)
    sparse_top = next((c for c in passed if c.from_sparse), None)

    if dense_top and sparse_top:
        if dense_top.topic_id == sparse_top.topic_id:
            # 两路一致 → 加分
            for c in passed:
                c.combined_score = min(c.combined_score * 1.05, 1.0)
                c.cross_validation = "AGREE"
        else:
            # 两路分歧 → 降分
            for c in passed:
                c.combined_score *= 0.85
                c.cross_validation = "DISAGREE"
    else:
        # 单路存活 → 轻微降分
        for c in passed:
            c.combined_score *= 0.9
            c.cross_validation = "SINGLE_SOURCE"

    return candidates
```

---

#### 5.2.7 Layer 5 — 出口质量门（Output Quality Gate）

**防的是**：经过所有校验后，最优候选仍然不靠谱（边界 case、噪声数据）。

| 检查项 | 条件 | 不通过动作 |
|--------|------|------------|
| 无存活候选 | `passed_candidates` 为空 | verdict = MISS |
| 最优分数不足 | `max(combined_score) < 0.75` | verdict = MISS |
| 最优满足阈值 | `max(combined_score) >= 0.75` | verdict = HIT，取最高分候选 |

> **为什么最终阈值是 0.75？**
> 这是"宁可拒掉也不信错"的策略。召回命中一个不准的题目比直接生成一个新的更糟糕——生成的内容至少是 LLM 从零构造的、与查询高度绑定的；错误的召回可能导致用户看到完全不相关的题目。因此阈值偏保守。

```python
def output_quality_gate(candidates: list[RecallCandidate]) -> tuple[str, RecallCandidate | None]:
    passed = [c for c in candidates if c.passed]
    if not passed:
        return "MISS", None

    best = max(passed, key=lambda c: c.combined_score)
    if best.combined_score < 0.75:
        return "MISS", None

    return "HIT", best
```

---

#### 5.2.8 完整实现伪代码

```python
async def recall_node(state: AgentState) -> AgentState:
    state.status = "RECALLING"
    nc = state.normalized
    trace = []  # 每层的判定记录，写入 state 用于追踪

    # ── Layer 0: 输入门 ──
    gate0 = input_gate(nc)
    trace.append({"layer": 0, "result": gate0})
    if not gate0.pass_:
        state.verdict = "MISS"
        state.recall_results = []
        state.trace_detail = trace
        return state

    # ── Layer 1: 向量质量门 ──
    query_vector = embedding_model.encode(nc.core_concept)
    gate1 = embedding_quality_gate(query_vector)
    trace.append({"layer": 1, "result": gate1})
    if not gate1.pass_:
        state.status = "ERROR"
        state.error = gate1.reason
        state.trace_detail = trace
        return state

    # ── Layer 2: 混合检索 ──
    candidates, search_meta = hybrid_search(query_vector, nc.keywords, milvus_client)
    trace.append({"layer": 2, "candidates_before": len(candidates), "meta": search_meta})
    if len(candidates) == 0:
        state.verdict = "MISS"
        state.recall_results = []
        state.trace_detail = trace
        return state

    # ── Layer 3: 双分数校验 ──
    candidates = await dual_scoring(nc, candidates, llm_client, embedding_model)
    trace.append({
        "layer": 3,
        "passed": sum(1 for c in candidates if c.passed),
        "rejected": [{"id": c.topic_id, "reason": c.reject_reason} for c in candidates if not c.passed],
    })

    # ── Layer 4: 交叉验证门 ──
    candidates = cross_validation_gate(candidates)
    trace.append({"layer": 4, "cross_validation": [c.cross_validation for c in candidates if c.passed]})

    # ── Layer 5: 出口质量门 ──
    verdict, best = output_quality_gate(candidates)
    trace.append({"layer": 5, "verdict": verdict, "best_score": best.combined_score if best else None})

    state.verdict = "HIT" if verdict == "HIT" else "MISS"
    state.recall_results = candidates
    state.best_match = best
    state.trace_detail = trace
    state.status = "RECALLED"
    return state
```

---

#### 5.2.9 Milvus Collection 设计

```yaml
Collection Name: topic_embeddings
Fields:
  - id:              INT64 (主键, auto_id)
  - topic_id:        VARCHAR(64)      # 关联 PostgreSQL topic.id
  - core_concept:    VARCHAR(256)     # 用于生成 embedding 的源文本
  - embedding:       FLOAT_VECTOR(1024) # bge-large-zh 输出维度
  - domain:          VARCHAR(64)      # 分区键 + 过滤字段
  - keywords:        VARCHAR(512)     # 逗号分隔，用于 BM25 检索
  - difficulty:      INT64            # 难度 1-5

Index:
  - field: embedding
  - type: HNSW
  - metric_type: COSINE
  - params: { M: 16, efConstruction: 200 }

Search Params:
  - metric_type: COSINE
  - params: { ef: 128 }
  - limit: 10
  - output_fields: [topic_id, core_concept, domain, keywords, difficulty]
```

---

#### 5.2.10 防呆设计决策速查

| 层级 | 门禁名称 | 防什么 | 不通过时 |
|------|----------|--------|----------|
| L0 | 输入门 | 归一化节点输出了垃圾 | → 直接 MISS |
| L1 | 向量质量门 | Embedding 模型异常 | → ERROR |
| L2 | 混合检索 | 单路搜索盲区 | 双路均空 → MISS |
| L3 | 双分数校验 | 向量相似度幻觉 (Score A 高但语义不相关) | 单候选淘汰或全淘汰 |
| L4 | 交叉验证门 | Dense vs Sparse 矛盾 | 降分，但不直接淘汰 |
| L5 | 出口质量门 | 所有候选最终都不合格 | → MISS |

---

### 5.3 VERIFY — 路由决策

**职责**：读取 RECALL 节点的判定结果，执行 LangGraph 条件边分流。

> RECALL 节点已完成全部校验，VERIFY 节点不做额外判断，仅做路由。这是对 v1 设计的简化——校验逻辑统一收口在 RECALL 内部，避免两个节点各自维护校验规则造成不一致。

**实现**：

```python
def verify_node(state: AgentState) -> AgentState:
    """VERIFY 仅做路由，不追加校验逻辑"""
    state.status = "VERIFYING"

    if state.verdict == "HIT":
        state.status = "VERIFIED_HIT"
    else:
        state.status = "VERIFIED_MISS"

    return state


def decide_after_verify(state: AgentState) -> str:
    """LangGraph 条件边决策函数"""
    return "hit" if state["verdict"] == "HIT" else "miss"
```

**状态转换**：

```
RECALLED → VERIFYING → VERIFIED_HIT  → RESPOND
                      → VERIFIED_MISS → GENERATE
```

---

### 5.4 GENERATE — Gen_skill 兜底生成

**职责**：当召回失败时，调用 LLM 从零生成完整面试题结构化数据。

**输入**：`NormalizedQuery` 中的 `core_concept` + `domain` + `keywords`

**输出**：完整 Topic JSON（与 v1 的 `skill_v2.md` 输出 schema 兼容）

```python
# 简化的输出结构（实际包含 9 张关联表数据）
{
  "topic": {
    "topic": "哈希表底层实现",
    "domain": "数据结构",
    "category": "哈希表",
    "difficulty": 3,
    "core_summary": "...",
    "core_points": ["..."],
    "detailed_explanation": "...",
    "code_example": "...",
    ...
  },
  "prerequisites": [...],
  "core_concepts": [...],
  "derivatives": [...],
  "extensions": [...],
  "evaluation_anchors": [...],
  "similar_questions": [...],
  "advanced_questions": [...],
  "references": [...]
}
```

**实现细节**：

| 步骤 | 操作 | 工具 |
|------|------|------|
| 1 | 构建 prompt（含归一化信息作为上下文） | 文本拼接 |
| 2 | LLM 调用，Structured Output 模式 | `llm.with_structured_output(TopicSchema)` |
| 3 | JSON 解析与字段校验 | Pydantic 模型验证 |
| 4 | 写入状态 | 更新 `AgentState.generated_topic` |

**LLM 配置**：
- Temperature: 0.7（生成需要一定创造性）
- Max Tokens: 4096
- Structured Output: ON（强制 JSON Schema 约束）

**Skill Prompt 路径**：`src/skills/gen_skill.md`

---

### 5.5 DUAL_WRITE — 双写

**职责**：将生成的内容同时写入 PostgreSQL（结构化）和 Milvus（向量），保证最终一致性。

**一致性策略 — Outbox Pattern**：

```
1. 开启 PG 事务
2. 写入所有 Topic 相关表 (topic + 8 关联表)
3. 写入 Outbox 表 (event_type="TOPIC_CREATED", payload=...)
4. 提交 PG 事务                           ← 主路径保证原子性
5. 尝试同步写入 Milvus                     ← 非阻塞，失败不影响主路径
6. 如果 Milvus 写入成功 → 标记 Outbox 为 PROCESSED
7. 如果 Milvus 写入失败 → 定时任务从 Outbox 消费重试
```

**Outbox 表结构**：

```sql
CREATE TABLE outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(64) NOT NULL,        -- TOPIC_CREATED
    payload JSONB NOT NULL,                  -- {"topic_id": "...", "core_concept": "..."}
    status VARCHAR(16) DEFAULT 'PENDING',    -- PENDING / PROCESSED / FAILED
    retry_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    processed_at TIMESTAMPTZ
);
```

**实现细节**：

| 步骤 | 操作 | 工具 |
|------|------|------|
| 1 | 开启 PG 事务 | `async with in_transaction()` |
| 2 | 写入 Topic 主表 + 8 张关联表（bulk_create） | Tortoise ORM |
| 3 | 写入 Outbox 记录 | Tortoise ORM |
| 4 | 提交事务 | 自动提交 |
| 5 | 生成 embedding 向量 | `bge-large-zh.encode(core_concept)` |
| 6 | 插入 Milvus Collection | `milvus.insert()` + `milvus.flush()` |
| 7 | 成功 → 更新 Outbox status=PROCESSED | Tortoise ORM |
| 8 | 失败 → 记录日志，Outbox 保持 PENDING | 定时任务补偿 |

---

### 5.6 RESPOND — 响应组装

**职责**：根据 Agent 执行路径组装最终响应。

**HIT 路径响应**（召回命中）：

```json
{
  "success": true,
  "source": "recall",
  "topic_id": "uuid",
  "topic_name": "哈希表底层实现",
  "domain": "数据结构",
  "difficulty": 3,
  "confidence": 0.91,
  "recall_score": 0.92,
  "recall_checks": {
    "similarity": 0.93,
    "keyword_overlap": 0.67,
    "domain_match": true
  },
  "trace_id": "abc-123"
}
```

**MISS 路径响应**（兜底生成）：

```json
{
  "success": true,
  "source": "generated",
  "topic_id": "uuid",
  "topic_name": "哈希表底层实现",
  "domain": "数据结构",
  "difficulty": 3,
  "confidence": 0.88,
  "recall_scores": [],
  "generation_model": "MiniMax-M2.7",
  "trace_id": "abc-123"
}
```

**ERROR 路径响应**：

```json
{
  "success": false,
  "error_code": "NORMALIZE_UNSUPPORTED_DOMAIN",
  "message": "输入超出技术面试题范围",
  "trace_id": "abc-123"
}
```

---

## 六、链路追踪设计

### 6.1 追踪架构

```
┌──────────────────────────────────────────────┐
│               Application Code                │
│  ┌────────┐  ┌────────┐  ┌────────────────┐  │
│  │ Node 1 │  │ Node 2 │  │ LangChain LLM  │  │
│  │ (Span) │  │ (Span) │  │   (Span)       │  │
│  └───┬────┘  └───┬────┘  └───────┬────────┘  │
│      │            │               │           │
│  ┌───┴────────────┴───────────────┴────────┐  │
│  │       OpenTelemetry SDK                  │  │
│  │  (自动采集 + 手动插桩)                    │  │
│  └──────────────────┬──────────────────────┘  │
└─────────────────────┼─────────────────────────┘
                      │ OTLP (gRPC/HTTP)
         ┌────────────┼────────────┐
         ▼            ▼            ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ LangFuse │ │  Jaeger  │ │  自定义   │
   │(LLM特化) │ │(分布式)  │ │  存储    │
   └──────────┘ └──────────┘ └──────────┘
```

### 6.2 核心数据结构

```python
class AgentState(TypedDict):
    # 业务数据
    trace_id: str                          # UUID v4, 贯穿全链路
    status: str                            # 当前状态机状态
    user_input: str                        # 用户原始输入
    normalized: NormalizedQuery | None     # 归一化结果
    recall_results: list[RecallCandidate]  # 召回候选列表（含 5 层校验的中间分数）
    verdict: str                           # HIT / MISS（由 RECALL L5 出口判定）
    best_match: RecallCandidate | None     # 最佳匹配候选（含 score_a, score_b, combined_score）
    generated_topic: dict | None           # Gen_skill 生成结果
    topic_id: str | None                   # 最终 topic ID

    # RECALL 防呆追踪（每个 Layer 的判定记录）
    trace_detail: list[dict]               # [{layer: 0, result: ...}, {layer: 1, result: ...}, ...]

    # 追踪数据（每个节点追加）
    state_history: list[StateTransition]   # 状态转换日志
    node_timings: dict[str, float]         # 每个节点耗时(ms)
    errors: list[dict]                     # 错误记录

class RecallCandidate(TypedDict):
    topic_id: str
    core_concept: str
    domain: str
    keywords: list[str]
    rrf_score: float                       # Layer 2 RRF 融合分
    from_dense: bool                       # 是否来自 Dense 路径
    from_sparse: bool                      # 是否来自 Sparse 路径
    score_a: float | None                  # Layer 3 Score A: 向量余弦
    score_b: float | None                  # Layer 3 Score B: NL 语义匹配
    nl_reasoning: str                      # Score B 的 LLM 判定理由
    combined_score: float                  # 最终综合分 (A×0.5 + B×0.5, 经 L4 调整)
    passed: bool                           # 是否通过全部校验
    reject_reason: str | None              # 淘汰原因
    cross_validation: str                  # AGREE / DISAGREE / SINGLE_SOURCE

class StateTransition(TypedDict):
    from_state: str
    to_state: str
    timestamp: str                         # ISO 8601
    reason: str                            # 转换原因，如 "similarity=0.62 < threshold=0.85"
    duration_ms: float                     # 上节点耗时
```

### 6.3 追踪示例

一次完整 MISS 路径的 trace（含 RECALL 内部 5 层防呆追踪）：

```
trace_id = "a1b2c3d4-..."
├─ [   0 ms] IDLE → NORMALIZING
├─ [1200 ms] NORMALIZING → NORMALIZED  | confidence=0.92, core_concept="线程池底层实现"
├─ [1300 ms] NORMALIZED → RECALLING
│
│   ┌── RECALL 内部防呆追踪 ──────────────────────────┐
│   ├─ [1305 ms] L0 输入门 PASS       | core_concept OK, confidence 0.92 ≥ 0.7
│   ├─ [1310 ms] L1 向量质量 PASS      | dim=1024, no NaN, self_sim=1.0000
│   ├─ [1320 ms] L2 混合检索           | dense=7 hits, sparse=4 hits, RRF merged=8
│   ├─ [1350 ms] L3 双分数校验          |
│   │   ├─ cand#1 "数据库连接池"       | A=0.88 ✓ B=0.15 ✗ → REJECT (相同"池"字, 概念不同)
│   │   ├─ cand#2 "Java 线程安全"      | A=0.82 ✓ B=0.55 ✗ → REJECT (相关但非核心匹配)
│   │   └─ cand#3 "进程与线程区别"     | A=0.71 ✗ → REJECT (Score A 不达标, 不调 LLM)
│   ├─ [1600 ms] L4 交叉验证           | DENSE≠SPARSE → DISAGREE, score×0.85
│   └─ [1605 ms] L5 出口质量门         | passed=0 → verdict=MISS
│
├─ [1610 ms] RECALLED → VERIFYING
├─ [1612 ms] VERIFYING → VERIFIED_MISS | 路由: RECALL 已判定 MISS
├─ [1615 ms] VERIFIED_MISS → GENERATING
├─ [5200 ms] GENERATING → GENERATED    | model=MiniMax-M2.7, tokens=2847
├─ [5210 ms] GENERATED → DUAL_WRITING
├─ [5450 ms] DUAL_WRITING → WRITTEN    | pg_ms=180, milvus_ms=55
├─ [5460 ms] WRITTEN → RESPONDING
└─ [5480 ms] RESPONDING → DONE


一次 HIT 路径的 trace（对比）：

trace_id = "e5f6g7h8-..."
├─ [   0 ms] IDLE → NORMALIZING
├─ [1100 ms] NORMALIZING → NORMALIZED  | confidence=0.95, core_concept="HashMap底层实现"
├─ [1110 ms] NORMALIZED → RECALLING
│
│   ┌── RECALL 内部防呆追踪 ──────────────────────────┐
│   ├─ [1115 ms] L0 输入门 PASS       | core_concept OK, confidence 0.95 ≥ 0.7
│   ├─ [1120 ms] L1 向量质量 PASS      | dim=1024, no NaN, self_sim=1.0000
│   ├─ [1130 ms] L2 混合检索           | dense=8 hits, sparse=6 hits, RRF merged=8
│   ├─ [1180 ms] L3 双分数校验          |
│   │   ├─ cand#1 "HashMap 实现原理"   | A=0.93 ✓ B=0.95 ✓ → combined=0.94
│   │   ├─ cand#2 "哈希表底层结构"     | A=0.89 ✓ B=0.90 ✓ → combined=0.90
│   │   └─ cand#3 "Java Map 接口"      | A=0.78 ✓ B=0.60 ✗ → REJECT (Score B 不够)
│   ├─ [1400 ms] L4 交叉验证           | DENSE=SPARSE → AGREE, score×1.05
│   └─ [1405 ms] L5 出口质量门         | best=cand#1, combined=0.99 → verdict=HIT
│
├─ [1410 ms] RECALLED → VERIFYING
├─ [1412 ms] VERIFYING → VERIFIED_HIT  | 路由: RECALL 已判定 HIT, best=HashMap实现原理
├─ [1415 ms] VERIFIED_HIT → RESPONDING
└─ [1420 ms] RESPONDING → DONE
```

### 6.4 实现方案

| 组件 | 工具 | 集成方式 |
|------|------|----------|
| Span 管理 | OpenTelemetry SDK | 在每个 Node 入口/出口手动 `start_span` / `end_span` |
| LLM 追踪 | LangFuse Callback | `langfuse.langchain.CallbackHandler` 作为 LangChain callback |
| 指标导出 | OTLP Exporter | `opentelemetry-exporter-otlp` → LangFuse / Jaeger |
| 日志关联 | `trace_id` 注入日志 | `logging` + `trace_id` Filter |

---

## 七、错误处理与补偿

### 7.1 错误分级

| 级别 | 场景 | 处理策略 |
|------|------|----------|
| **Fatal** | LLM API Key 无效、PG 连接拒绝、Milvus 不可达 | Agent 状态 → ERROR，返回 500 |
| **Degraded** | 归一化 LLM 超时、Milvus 查询超时 | 降级路径，继续执行 |
| **Recoverable** | Milvus 写入失败 | Outbox 补偿，不阻塞主流程 |
| **Ignorable** | 链路追踪上报失败 | 静默忽略，不影响业务 |

### 7.2 降级路径

```
正常路径:          NORMALIZE → RECALL → VERIFY → {HIT|MISS} → ...
归一化降级:        [归一化超时] → 原文作为 core_concept → RECALL
召回降级:          [Milvus 不可达] → recall_results=[] → VERIFY → MISS → GENERATE
生成降级:          [LLM 超时] → 返回通用错误，不阻塞
```

### 7.3 Outbox 补偿消费者

```python
# 后台定时任务，每 30 秒执行一次
async def outbox_compensation_worker():
    while True:
        pending = await Outbox.filter(
            status="PENDING",
            retry_count__lt=3
        ).limit(10)

        for event in pending:
            try:
                # 重新生成 embedding 并插入 Milvus
                await retry_milvus_insert(event.payload)
                event.status = "PROCESSED"
            except Exception:
                event.retry_count += 1
                if event.retry_count >= 3:
                    event.status = "FAILED"
            await event.save()

        await asyncio.sleep(30)
```

---

## 八、项目目录结构

```
TopicSystem/
├── pyproject.toml
├── .env.example
├── .gitignore
├── docker-compose.yml              # PostgreSQL 16 + Milvus 2.4 standalone
├── README.md                       # 项目说明
├── DESIGN.md                       # 本文档
│
├── src/
│   ├── main.py                     # FastAPI 入口 + Agent Graph 注册
│   │
│   ├── agent/                      # Agent Loop 核心
│   │   ├── __init__.py
│   │   ├── graph.py                # StateGraph 构建 + 条件边定义
│   │   ├── state.py                # AgentState TypedDict + 状态枚举 + 数据模型
│   │   └── nodes/
│   │       ├── __init__.py
│   │       ├── normalize.py        # 语义归一化节点
│   │       ├── recall.py           # Milvus 向量召回节点
│   │       ├── verify.py           # 多维度校验节点
│   │       ├── generate.py         # Gen_skill 兜底生成节点
│   │       ├── dual_write.py       # PG + Milvus 双写节点（含 Outbox）
│   │       └── respond.py          # 响应组装节点
│   │
│   ├── tools/                      # 可复用工具
│   │   ├── __init__.py
│   │   ├── embedding.py            # bge-large-zh 编码器封装
│   │   ├── milvus_client.py        # Milvus CRUD + Search 封装
│   │   └── llm_client.py           # LangChain LLM 单例（含 Structured Output）
│   │
│   ├── models/                     # Tortoise ORM 数据模型
│   │   ├── __init__.py
│   │   ├── topic.py                # 面试题主表
│   │   ├── topic_prerequisite.py
│   │   ├── topic_core_concept.py
│   │   ├── topic_derivative.py
│   │   ├── topic_extension.py
│   │   ├── topic_evaluation_anchor.py
│   │   ├── topic_similar_question.py
│   │   ├── topic_advanced_question.py
│   │   ├── topic_reference.py
│   │   ├── topic_review_log.py
│   │   ├── outbox.py               # 补偿任务表
│   │   └── prompt_template.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── topic_api.py            # POST /api/v2/topic/generate, GET /trace/{id}
│   │   └── healthcheck.py          # GET /health
│   │
│   ├── skills/                     # Skill Prompt 文件
│   │   ├── normalize_skill.md      # 归一化 Prompt（含能力边界定义）
│   │   ├── gen_skill.md            # 兜底生成 Prompt
│   │   └── verify_skill.md         # 校验规则参考（可选）
│   │
│   ├── tracing/                    # 链路追踪
│   │   ├── __init__.py
│   │   └── tracer.py               # OpenTelemetry + LangFuse 初始化
│   │
│   ├── workers/                    # 后台任务
│   │   ├── __init__.py
│   │   └── outbox_worker.py        # Outbox 补偿消费者
│   │
│   └── config/
│       ├── __init__.py
│       ├── settings.py             # Pydantic BaseSettings（环境变量）
│       └── llm_config.py           # LLM / Embedding 模型注册
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_normalize.py           # 归一化节点单元测试
│   ├── test_recall.py              # 召回节点单元测试
│   ├── test_verify.py              # 校验节点单元测试
│   ├── test_generate.py            # 生成节点单元测试
│   ├── test_dual_write.py          # 双写节点单元测试
│   └── test_agent_flow.py          # 端到端 Agent 流程集成测试
│
└── scripts/
    ├── init_milvus.py              # Milvus Collection Schema 初始化
    └── seed_data.py                # 种子数据导入
```

---

## 九、依赖清单 (pyproject.toml)

```toml
[tool.poetry.dependencies]
python = "^3.12"
fastapi = ">=0.115.0"
uvicorn = ">=0.43.0"
tortoise-orm = ">=0.24.0"
aerich = ">=0.7.0"
pydantic = ">=2.0"
pydantic-settings = ">=2.13.0"
python-dotenv = ">=1.2.0"

# Agent
langgraph = ">=0.2.0"
langchain = ">=0.3.0"
langchain-openai = ">=0.3.0"
langchain-community = ">=0.3.0"

# Vector DB
pymilvus = ">=2.4.0"

# Embedding
sentence-transformers = ">=3.0.0"

# Tracing
opentelemetry-api = ">=1.20"
opentelemetry-sdk = ">=1.20"
opentelemetry-exporter-otlp = ">=1.20"
langfuse = ">=2.0.0"

# Async
aio-pika = ">=9.4.0"

[tool.poetry.group.dev.dependencies]
pytest = ">=8.0"
pytest-asyncio = ">=0.24"
httpx = ">=0.27"
ruff = ">=0.5"
```

---

## 十、实施计划

| 阶段 | 内容 | 预计工作量 |
|------|------|-----------|
| **Phase 1 — 基础设施** | `.gitignore`、`docker-compose.yml`（PG + Milvus）、Poetry 依赖安装、`init_milvus.py` | 0.5d |
| **Phase 2 — 工具层** | `embedding.py`、`milvus_client.py`、`llm_client.py` 三大工具封装 | 1d |
| **Phase 3 — Agent 状态机** | `state.py`（数据模型 + 状态枚举）+ `graph.py`（StateGraph 构建） | 0.5d |
| **Phase 4 — 节点实现** | 按 `normalize → recall → verify → generate → dual_write → respond` 顺序实现 6 个节点 | 2d |
| **Phase 5 — API 接入** | FastAPI endpoint 接入 Agent Graph，SSE 流式输出 | 0.5d |
| **Phase 6 — 链路追踪** | OpenTelemetry SDK 插桩 + LangFuse Callback 集成 | 0.5d |
| **Phase 7 — 补偿机制** | Outbox 表 + 后台 Worker | 0.5d |
| **Phase 8 — 测试** | 节点单元测试 + 端到端集成测试 | 1d |
| **Phase 9 — 清理 v1** | 移除死代码（`llm_service.py`、`genTopicController.py`、`analysis.py`），修复已知 Bug | 0.5d |

---

## 十一、附录

### A. 与 v1 的核心变化

| 维度 | v1 | v2 |
|------|----|----|
| 执行模型 | 线性流水线（API → Service → LLM → DB） | Agent Loop 状态机（LangGraph） |
| 召回 | 无，每次全新生成 | Milvus 向量召回 + 命中直接返回 |
| 归一化 | 简单 LLM 调用 | 结构化 LLM + 显式能力边界 + JSON Schema |
| 写入 | 仅 PG | PG + Milvus 双写（Outbox 最终一致） |
| 校验 | 无 | 三维度校验（语义+关键词+领域） |
| 追踪 | `print()` 日志 | OpenTelemetry + LangFuse |
| 错误处理 | 异常冒泡 | 分级 + 降级路径 + Outbox 补偿 |

### B. 关键阈值速查

| 参数 | 值 | 位置 |
|------|-----|------|
| **NORMALIZE** | | |
| 归一化置信度下限 | 0.70 | `normalize.py` |
| 归一化 core_concept 最小长度 | 2 字符 | `recall.py` L0 |
| **RECALL** | | |
| Layer 0 — 输入门置信度下限 | 0.70 | `recall.py` L0 |
| Layer 1 — Embedding 维度 | 1024 | `recall.py` L1 |
| Layer 1 — 自相似度下限 | 0.9999 | `recall.py` L1 |
| Layer 2 — Dense 检索 limit | 10（非最终 5） | `recall.py` L2 |
| Layer 2 — Sparse 检索 limit | 10 | `recall.py` L2 |
| Layer 2 — RRF k 常数 | 60 | `recall.py` L2 |
| Layer 3 — Score A 余弦阈值 | 0.75 | `recall.py` L3 |
| Layer 3 — Score B NL 语义阈值 | 0.70 | `recall.py` L3 |
| Layer 4 — Dense/Sparse 分歧降分 | ×0.85 | `recall.py` L4 |
| Layer 4 — 单路存活降分 | ×0.90 | `recall.py` L4 |
| Layer 4 — 两路一致加分 | ×1.05 | `recall.py` L4 |
| Layer 5 — 出口综合分阈值 | 0.75 | `recall.py` L5 |
| **GENERATE** | | |
| LLM Temperature | 0.7 | `generate.py` |
| LLM Max Tokens | 4096 | `generate.py` |
| **COMPENSATION** | | |
| Outbox 重试上限 | 3 次 | `outbox_worker.py` |
| Outbox 轮询间隔 | 30 秒 | `outbox_worker.py` |
