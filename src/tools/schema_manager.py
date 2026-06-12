"""
Schema Manager —— 提取 Tortoise ORM 模型元数据，编码后写入 Milvus table_schemas 集合
供 query_database capability 动态检索相关表结构使用
"""
from src.tools.embedding import EmbeddingEncoder
from src.tools.milvus_client import MilvusClient

# 每张表的人类可读描述 —— 用于 BGE 语义编码
# key: table_name, value: (description, schema_text)
_KNOWN_SCHEMAS: dict[str, tuple[str, str]] = {}

_MODULES_LOADED = False


def _ensure_loaded():
    """延迟加载模型描述（避免循环导入）"""
    global _MODULES_LOADED
    if _MODULES_LOADED:
        return
    _MODULES_LOADED = True

    _KNOWN_SCHEMAS["topic"] = (
        "面试题主表，存储技术面试题目的核心内容。包含题目名称(topic)、别名(alias)、难度(difficulty)、一级领域(domain)、"
        "技术域(tech_domain 后端开发/前端开发/数据科学/运维)、二级分类(category)、标签(tags)、关键词(keywords)、"
        "一句话概述(one_liner)、核心概述(core_summary)、核心要点(core_points)、详细解释(detailed_explanation)、"
        "代码示例(code_example)、面试陷阱(traps)、加分回答(bonuses)、复习时间等信息。"
        "查询场景：按难度筛选题目、按技术域/分类浏览题库、搜索题目内容。",
        "topic(id, topic, alias, domain, tech_domain, category, tags, difficulty, keywords, one_liner, core_summary, core_points, detailed_explanation, code_example, traps, bonuses, mastery_level, review_count, last_reviewed, next_review, created_at, updated_at)"
    )

    _KNOWN_SCHEMAS["knowledge_dict"] = (
        "知识点词典，存储所有题目引用的独立知识点名称(name)和描述(description)。"
        "同名知识点自动去重，多道题可共享同一知识点。"
        "查询场景：查看知识点列表、按知识点名称查找、统计知识点被引用次数。",
        "knowledge_dict(id, name UNIQUE, description, created_at)"
    )

    _KNOWN_SCHEMAS["knowledge_alias"] = (
        "知识点别名表，存储知识点的同义名称映射。"
        "knowledge_id关联到knowledge_dict，alias存储别名（如'红黑树结构'→'红黑树'）。"
        "查询场景：搜索时为同义知识点做归一化匹配。",
        "knowledge_alias(id, knowledge_id→knowledge_dict, alias, UNIQUE(knowledge_id,alias))"
    )

    _KNOWN_SCHEMAS["topic_prerequisite"] = (
        "前置知识点关联，记录题目的前置知识关系。"
        "包含topic_id(→topic)、knowledge_id(→knowledge_dict)、importance重要性(1-5)和sort_order排序。"
        "查询场景：找题目的前置知识、找某知识点的前置题目、面试官查用户盲区。",
        "topic_prerequisite(id, topic_id→topic, knowledge_id→knowledge_dict, importance, sort_order, UNIQUE(topic_id,knowledge_id))"
    )

    _KNOWN_SCHEMAS["topic_core_concept"] = (
        "核心概念关联，记录题目的核心子概念。"
        "结构与topic_prerequisite相同。查询场景：找题目的核心概念、面试官根据用户表现追问子概念。",
        "topic_core_concept(id, topic_id→topic, knowledge_id→knowledge_dict, importance, sort_order, UNIQUE(topic_id,knowledge_id))"
    )

    _KNOWN_SCHEMAS["topic_derivative"] = (
        "衍生知识点关联，记录题目的衍生变体（跨上下文的关联）。"
        "如HashMap→ConcurrentHashMap(并发)、HashMap→TreeMap(有序)。"
        "结构与topic_prerequisite相同。查询场景：面试官在用户答得好时递进到衍生题目。",
        "topic_derivative(id, topic_id→topic, knowledge_id→knowledge_dict, importance, sort_order, UNIQUE(topic_id,knowledge_id))"
    )

    _KNOWN_SCHEMAS["topic_extension"] = (
        "扩展延伸关联，记录题目的深度扩展（同技术域的深层话题）。"
        "如HashMap→哈希算法设计、HashMap→扩容机制详解。"
        "结构与topic_prerequisite相同。查询场景：面试官在用户水平高时向上延伸。",
        "topic_extension(id, topic_id→topic, knowledge_id→knowledge_dict, importance, sort_order, UNIQUE(topic_id,knowledge_id))"
    )

    _KNOWN_SCHEMAS["topic_evaluation_anchor"] = (
        "评估基准，存储各级难度(level: entry/master/expert)的面试题(question)和标准答案(expected_answer)。"
        "查询场景：面试官出题时获取针对题目的各级面试题和答案参考。",
        "topic_evaluation_anchor(id, topic_id→topic, level, question, expected_answer, sort_order)"
    )

    _KNOWN_SCHEMAS["topic_similar_question"] = (
        "相关面试题，存储与题目相关的其他面试问题(question)和答题提示(answer_hint)。"
        "查询场景：为用户展示相关题目列表。",
        "topic_similar_question(id, topic_id→topic, question, answer_hint, sort_order)"
    )

    _KNOWN_SCHEMAS["topic_advanced_question"] = (
        "进阶面试题，存储进阶问题(question)和答题提示(answer_hint)。"
        "查询场景：为用户展示更高难度的延伸问题。",
        "topic_advanced_question(id, topic_id→topic, question, answer_hint, sort_order)"
    )

    _KNOWN_SCHEMAS["topic_reference"] = (
        "参考资源，存储题目的参考文档链接。包含标题(title)、URL(url)和描述(description)。"
        "查询场景：为用户展示推荐阅读材料。",
        "topic_reference(id, topic_id→topic, title, url, description, sort_order)"
    )

    _KNOWN_SCHEMAS["user_topic_status"] = (
        "用户掌握状态，记录用户(user_id)对每道题(topic_id)的掌握程度(status: mastered/learning)。"
        "查询场景：查询用户已掌握/未掌握的题目、按用户状态筛选题目。UNIQUE(user_id,topic_id)。",
        "user_topic_status(id, user_id, topic_id→topic, status, updated_at, UNIQUE(user_id,topic_id))"
    )


def _encode_text(text: str) -> list[float]:
    encoder = EmbeddingEncoder.get_instance()
    if not encoder.available:
        return []
    vec = encoder.encode(text)
    return vec.tolist()


def sync_table_schemas_to_milvus() -> int:
    """
    提取所有已知的表元数据并写入 Milvus table_schemas 集合。
    启动时调用，根据 Milvus 是否有数据决定是否写入。
    返回写入数量。Milvus 不可用返回 0。
    """
    milvus = MilvusClient.get_instance()
    if not milvus.available:
        return 0

    milvus.init_table_schemas_collection()

    existing_count = milvus.count_table_schemas()
    if existing_count > 0:
        return existing_count  # 已有数据，跳过

    _ensure_loaded()
    count = 0
    for table_name, (description, schema_text) in _KNOWN_SCHEMAS.items():
        search_text = f"{table_name}: {description}"
        embedding = _encode_text(search_text)
        if not embedding:
            continue
        milvus.upsert_table_schema(table_name, description, schema_text, embedding)
        count += 1

    return count


def search_relevant_tables(query: str, top_k: int = 8) -> list[dict]:
    """
    根据自然语言查询意图，从 Milvus 中检索最相关的表结构。
    Milvus 不可用时返回空列表。
    返回: [{"table_name": str, "description": str, "schema_text": str, "score": float}, ...]
    """
    milvus = MilvusClient.get_instance()
    if not milvus.available:
        return []

    if milvus.count_table_schemas() == 0:
        _ensure_loaded()
        return [
            {"table_name": tn, "description": desc, "schema_text": st, "score": 0.0}
            for tn, (desc, st) in _KNOWN_SCHEMAS.items()
        ]

    embedding = _encode_text(query)
    if not embedding:
        return []

    return milvus.search_table_schemas(embedding, top_k)


def build_schema_prompt(query: str) -> str:
    """
    根据查询意图构建表结构 prompt 段，直接注入到 query_skill prompt 中。

    Milvus 可用时 → 只包含语义相关的 top-k 表
    Milvus 不可用时 → 包含全部表
    """
    hits = search_relevant_tables(query)
    if not hits:
        return "（无可用的表结构信息）"

    lines = ["## 当前可用的数据库表（根据查询意图自动匹配）\n"]
    for i, h in enumerate(hits):
        lines.append(f"### {h['table_name']}")
        lines.append(f"{h['description']}")
        lines.append(f"```sql\n{h['schema_text']}\n```")
        if h.get("score", 0) > 0:
            lines.append(f"（相关度：{h['score']:.2f}）")
        lines.append("")

    return "\n".join(lines)
