"""
全链路测试: 使用已有 JSON 数据

跳过 LLM 调用，直接测试语义转换 + 落库链路
"""
import asyncio
import json
import re
import os

# 设置路径
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.service.topic_service import TopicService
from src.service.semantic_trans import semantic_convert


async def test_semantic_and_save():
    """测试语义转换 + 使用已有JSON + 落库"""
    print("=" * 60)
    print("链路测试: 语义转换 + 使用已有JSON + 落库")
    print("=" * 60)
    
    # 步骤1: 语义转换
    user_input = "HashMap底层实现"
    print(f"\n[Step 1] 语义转换: {user_input}")
    
    trans_result = semantic_convert(user_input)
    if not trans_result.success:
        print(f"  ❌ 失败: {trans_result.code}")
        return False
    
    print(f"  ✅ 成功: {trans_result.data.standardized_output}")
    print(f"  置信度: {trans_result.data.confidence}")
    
    # 步骤2: 读取已有 JSON
    json_file = 'src/service/json_output/面试题_HashMap_20260428_071828.json'
    print(f"\n[Step 2] 读取已有 JSON: {json_file}")
    
    with open(json_file, 'r') as f:
        raw_content = f.read()
    
    json_blocks = re.findall(r'```json\s*([\s\S]*?)\s*```', raw_content)
    if not json_blocks:
        print(f"  ❌ 未找到 JSON 块")
        return False
    
    topic_data = json.loads(json_blocks[0].strip())
    print(f"  ✅ 成功: keys={list(topic_data.keys())}")
    
    # 步骤3: 落库
    print(f"\n[Step 3] 执行落库...")
    service = TopicService()
    
    try:
        topic = await service.save_topic(topic_data)
        print(f"  ✅ 成功!")
        print(f"    topic_id: {topic.id}")
        print(f"    topic_name: {topic.topic}")
        print(f"    domain: {topic.domain}")
        print(f"    difficulty: {topic.difficulty}")
        print(f"    alias: {topic.alias}")
        print(f"    tags: {topic.tags}")
        
        # 验证关联数据
        from src.models.topic_prerequisite import TopicPrerequisite
        from src.models.topic_core_concept import TopicCoreConcept
        from src.models.topic_evaluation_anchor import TopicEvaluationAnchor
        
        prereqs = await TopicPrerequisite.filter(topic=topic).count()
        concepts = await TopicCoreConcept.filter(topic=topic).count()
        anchors = await TopicEvaluationAnchor.filter(topic=topic).count()
        
        print(f"\n[验证] 关联数据:")
        print(f"  prerequisites: {prereqs} 条")
        print(f"  core_concepts: {concepts} 条")
        print(f"  evaluation_anchors: {anchors} 条")
        
        print("\n" + "=" * 60)
        print("✅ 全链路测试成功!")
        return True
        
    except Exception as e:
        print(f"  ❌ 失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    # 初始化数据库
    from tortoise import Tortoise
    from dotenv import load_dotenv
    
    load_dotenv('.env')
    
    await Tortoise.init(
        db_url=os.getenv('DATABASE_URL'),
        modules={'models': ['src.models']}
    )
    
    # 清理测试数据
    from src.models.topic import Topic
    await Topic.filter(topic='HashMap底层原理与面试深度解析').delete()
    
    # 执行测试
    success = await test_semantic_and_save()
    
    # 关闭连接
    await Tortoise.close_connections()
    
    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    if result:
        print("\n✅ 所有测试通过")
    else:
        print("\n❌ 测试失败")