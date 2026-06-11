"""
全链路测试脚本

测试完整流程：外部API -> 语义转换 -> Skill生成 -> 落库

直接调用 TopicAPI，无需启动服务器
"""
import asyncio
import os
from dotenv import load_dotenv

# 设置路径
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(".env")

from src.api.topic_api import GenerateTopicRequest, TopicAPI


async def test_full_flow():
    """全链路测试"""
    print("=" * 60)
    print("全链路测试: 外部API -> 语义转换 -> Skill生成 -> 落库")
    print("=" * 60)
    
    # 准备请求
    request = GenerateTopicRequest(
        user_input="HashMap底层实现",
        save_response=True
    )
    
    print(f"\n[请求] user_input: {request.user_input}")
    print("-" * 60)
    
    # 执行全链路
    api = TopicAPI()
    response = await api.generate_topic(request)
    
    # 输出结果
    print("\n[响应]")
    print("-" * 60)
    print(f"success: {response.success}")
    print(f"message: {response.message}")
    
    if response.topic:
        print("\n[Topic 信息]")
        print(f"  topic_id: {response.topic.topic_id}")
        print(f"  topic_name: {response.topic.topic_name}")
        print(f"  domain: {response.topic.domain}")
        print(f"  difficulty: {response.topic.difficulty}")
        if response.topic.alias:
            print(f"  alias: {response.topic.alias}")
        if response.topic.tags:
            print(f"  tags: {response.topic.tags}")
        if response.topic.keywords:
            print(f"  keywords: {response.topic.keywords}")
    
    if response.semantic_trans:
        print("\n[语义转换]")
        print(f"  standardized_output: {response.semantic_trans.standardized_output}")
        print(f"  confidence: {response.semantic_trans.confidence}")
    
    if response.error_code:
        print(f"\n[错误] error_code: {response.error_code}")
    if response.error_detail:
        print(f"[错误] error_detail: {response.error_detail}")
    
    print("\n" + "=" * 60)
    
    if response.success:
        print("✅ 全链路测试成功!")
    else:
        print("❌ 全链路测试失败!")
    
    return response.success


async def test_duplicate_protection():
    """测试防重逻辑"""
    print("\n" + "=" * 60)
    print("防重测试: 重复请求应该被拒绝")
    print("=" * 60)
    
    request = GenerateTopicRequest(
        user_input="HashMap底层实现",
        save_response=False
    )
    
    api = TopicAPI()
    
    print("\n[第一次请求]")
    response1 = await api.generate_topic(request)
    print(f"success: {response1.success}, message: {response1.message}")
    
    print("\n[第二次请求（应该失败）]")
    response2 = await api.generate_topic(request)
    print(f"success: {response2.success}, message: {response2.message}")
    
    print("\n" + "=" * 60)
    
    if response1.success and not response2.success:
        print("✅ 防重测试通过!")
        return True
    else:
        print("❌ 防重测试失败!")
        return False


async def main():
    """主函数"""
    try:
        # 测试1: 全链路
        success1 = await test_full_flow()
        
        if success1:
            # 测试2: 防重
            success2 = await test_duplicate_protection()
        
        print("\n\n" + "=" * 60)
        print("所有测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())