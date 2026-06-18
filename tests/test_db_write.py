import pytest

from src.agentv3.capabilities.write import save_to_postgres
from src.models.knowledge_dict import KnowledgeDict
from src.models.topic import Topic
from src.models.topic_core_concept import TopicCoreConcept
from src.models.topic_derivative import TopicDerivative
from src.models.topic_evaluation_anchor import TopicEvaluationAnchor
from src.models.topic_extension import TopicExtension
from src.models.topic_prerequisite import TopicPrerequisite
from src.models.topic_similar_question import TopicSimilarQuestion

pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.asyncio]

TOPIC_DATA = {
    "topic": {
        "topic": "HashMap底层实现",
        "alias": ["HashMap原理"],
        "domain": "编程基础",
        "tech_domain": "后端开发",
        "category": "Java",
        "tags": ["Java集合"],
        "difficulty": 3,
        "keywords": ["HashMap", "哈希表"],
        "one_liner": "HashMap是Java中基于哈希表实现的Map。",
        "core_summary": "HashMap底层由数组+链表+红黑树实现。",
        "core_points": ["数组+链表+红黑树"],
        "detailed_explanation": "详细解释...",
        "code_example": "int hash = ...;",
        "traps": "陷阱",
        "bonuses": "加分点",
    },
    "knowledge_points": [
        {"name": "哈希表", "type": "prerequisite", "importance": 5, "description": "理论基础"},
        {"name": "哈希冲突", "type": "core_concept", "importance": 5, "description": "核心"},
        {"name": "红黑树", "type": "core_concept", "importance": 4, "description": "数据结构"},
        {"name": "链表", "type": "core_concept", "importance": 4, "description": "数据结构"},
        {"name": "ConcurrentHashMap", "type": "derivative", "importance": 3, "description": "并发版"},
        {"name": "TreeMap", "type": "derivative", "importance": 2, "description": "有序版"},
        {"name": "哈希算法设计", "type": "extension", "importance": 3, "description": "原理"},
        {"name": "HashMap扩容机制详解", "type": "extension", "importance": 4, "description": "扩容"},
    ],
    "evaluation_anchors": [
        {"level": "entry", "question": "什么是HashMap？", "expected_answer": "A1"},
        {"level": "master", "question": "红黑树转换条件？", "expected_answer": "A2"},
        {"level": "expert", "question": "扩容机制？", "expected_answer": "A3"},
    ],
    "similar_questions": [
        {"question": "HashTable vs HashMap", "answer_hint": "线程安全"},
    ],
    "advanced_questions": [
        {"question": "为什么容量是2的幂？", "answer_hint": "位运算优化"},
    ],
    "references": [
        {"title": "HashMap源码", "url": "https://example.com", "description": "文档"},
    ],
}


async def test_save_to_postgres_full_topic(db):
    """save_to_postgres 全字段落库验证"""
    result = await save_to_postgres(TOPIC_DATA)
    tid = result["topic_id"]
    assert tid, "topic_id 应非空"

    assert await Topic.filter(id=tid).count() == 1
    assert await KnowledgeDict.all().count() >= 1
    assert await TopicPrerequisite.filter(topic_id=tid).count() >= 1
    assert await TopicCoreConcept.filter(topic_id=tid).count() >= 2
    assert await TopicDerivative.filter(topic_id=tid).count() >= 1
    assert await TopicExtension.filter(topic_id=tid).count() >= 1
    assert await TopicEvaluationAnchor.filter(topic_id=tid).count() == 3
    assert await TopicSimilarQuestion.filter(topic_id=tid).count() >= 1


if __name__ == "__main__":
    import asyncio
    print("此文件已转为 pytest 用例,请用 `pytest tests/test_db_write.py --run-e2e` 运行")
