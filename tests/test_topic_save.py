"""
TopicService save_topic 方法测试

测试从 JSON 文件读取数据并落库的完整流程
"""
import json
import re

import pytest
import pytest_asyncio

from src.service.topic_service import TopicService


@pytest.fixture
def json_file_path():
    """JSON 文件路径 fixture"""
    return 'src/service/json_output/面试题_HashMap_20260428_071828.json'


@pytest.fixture
def topic_data(json_file_path):
    """从 JSON 文件解析 topic_data fixture"""
    with open(json_file_path, 'r') as f:
        raw_content = f.read()
    
    json_blocks = re.findall(r'```json\s*([\s\S]*?)\s*```', raw_content)
    assert json_blocks, f"未找到 JSON 块: {json_file_path}"
    
    return json.loads(json_blocks[0].strip())


@pytest.mark.asyncio
async def test_save_topic_with_json(setup_db, topic_data):
    """测试 save_topic 方法从 JSON 数据落库"""
    from src.models.topic import Topic
    from src.models.topic_prerequisite import TopicPrerequisite
    from src.models.topic_core_concept import TopicCoreConcept
    from src.models.topic_evaluation_anchor import TopicEvaluationAnchor
    from src.models.topic_derivative import TopicDerivative
    from src.models.topic_extension import TopicExtension
    from src.models.topic_similar_question import TopicSimilarQuestion
    from src.models.topic_advanced_question import TopicAdvancedQuestion
    from src.models.topic_reference import TopicReference
    
    topic_name = topic_data["topic"]["topic"]
    
    # 清理旧数据（防重测试后的残留）
    await Topic.filter(topic=topic_name).delete()
    
    service = TopicService()
    
    # 执行 save_topic
    topic = await service.save_topic(topic_data)
    
    # 验证 Topic 主表
    assert topic.id is not None
    assert topic.topic == topic_name
    assert topic.alias == ['HashMap实现原理', '哈希表原理']
    assert topic.tags == ['高频', '必问', '原理', '实战']
    assert topic.keywords == ['HashMap', '哈希表', '数组', '链表', '红黑树', '扰动函数', '扩容', '负载因子']
    assert topic.domain == 'Java'
    assert topic.difficulty == 3
    
    # 验证关联表数据
    assert await TopicPrerequisite.filter(topic=topic).count() == 4
    assert await TopicCoreConcept.filter(topic=topic).count() == 5
    assert await TopicEvaluationAnchor.filter(topic=topic).count() == 3
    assert await TopicDerivative.filter(topic=topic).count() == 3
    assert await TopicExtension.filter(topic=topic).count() == 3
    assert await TopicSimilarQuestion.filter(topic=topic).count() == 3
    assert await TopicAdvancedQuestion.filter(topic=topic).count() == 2
    assert await TopicReference.filter(topic=topic).count() == 3
    
    # 验证 evaluation_anchors 的 level 和 content 字段
    anchors = await TopicEvaluationAnchor.filter(topic=topic).order_by('sort_order')
    assert anchors[0].level == '入门'
    assert anchors[0].content is not None
    assert anchors[1].level == '掌握'
    assert anchors[2].level == '精通'
    
    print(f"\n✅ test_save_topic_with_json 通过!")
    print(f"   topic_id: {topic.id}")
    print(f"   alias: {topic.alias}")
    print(f"   tags: {topic.tags}")
    print(f"   keywords: {topic.keywords}")
    print(f"   prerequisites: 4 条")
    print(f"   core_concepts: 5 条")
    print(f"   evaluation_anchors: 3 条")


@pytest.mark.asyncio
async def test_save_topic_duplicate_check(setup_db, topic_data):
    """测试 save_topic 防重逻辑"""
    from src.models.topic import Topic
    
    topic_name = topic_data["topic"]["topic"]
    
    # 确保数据存在
    await Topic.filter(topic=topic_name).delete()
    service = TopicService()
    topic = await service.save_topic(topic_data)
    
    # 再次保存应该抛出异常
    with pytest.raises(RuntimeError, match="already exists"):
        await service.save_topic(topic_data)
    
    print(f"\n✅ test_save_topic_duplicate_check 通过!")


@pytest.mark.asyncio
async def test_save_topic_invalid_data(setup_db):
    """测试 save_topic 空数据校验"""
    service = TopicService()
    
    # 空 topic 名称应该抛出异常
    with pytest.raises(ValueError, match="Topic name is required"):
        await service.save_topic({"topic": {"topic": ""}})
    
    # 缺少 topic 键应该抛出异常
    with pytest.raises(ValueError, match="Topic name is required"):
        await service.save_topic({})
    
    print(f"\n✅ test_save_topic_invalid_data 通过!")


if __name__ == '__main__':
    asyncio.run(test_save_topic_with_json(None))