"""
Topic 服务（整合层）
完整流程：语义转换 -> LLM生成面试题 -> 完整落库
负责协调 TopicLLMService 和 TopicDBService
"""
from typing import Iterator, AsyncIterator

from src.service.topic_llm import TopicLLMService
from src.service.topic_db import TopicDBService
from src.service.semantic_trans import semantic_convert
from src.common.semantic_error import SemanticResult, SemanticData, error_result, SemanticErrorCode


class TopicService:
    """Topic 服务 - 整合 LLM 和 DB 服务"""
    
    def __init__(self):
        self.llm_service = TopicLLMService()
        self.db_service = TopicDBService()
    
    def generate_topic(self, standardized_input: str, save_response: bool = True) -> dict:
        """
        调用 llm+skill 生成面试题（委托给 TopicLLMService）
        """
        return self.llm_service.generate_topic(standardized_input, save_response)
    
    def generate_topic_streaming(self, standardized_input: str) -> Iterator[str]:
        """
        流式调用 llm+skill 生成面试题
        """
        return self.llm_service.generate_topic_streaming(standardized_input)
    
    async def save_topic(self, topic_data: dict):
        """
        根据生成结果完整落库（委托给 TopicDBService）
        """
        return await self.db_service.save_topic(topic_data)
    
    async def get_topic_flow(self, user_input: str) -> SemanticResult:
        """
        完整流程：语义转换 -> 生成 -> 落库
        
        Args:
            user_input: 用户原始输入
            
        Returns:
            SemanticResult: 包含落库后的 Topic ID 或错误信息
        """
        # 1. 语义转换
        trans_result = semantic_convert(user_input)
        if not trans_result.success:
            return trans_result
        
        # 2. 获取标准化输出
        semantic_data = trans_result.data
        if not isinstance(semantic_data, SemanticData):
            return error_result(
                error_code=SemanticErrorCode.SERVICE_ERROR,
                original_input=user_input,
                suggestion="语义转换结果格式异常"
            )
        
        standardized_output = semantic_data.standardized_output
        
        # 3. 生成面试题
        try:
            topic_data = self.generate_topic(standardized_output)
        except Exception as e:
            return error_result(
                error_code=SemanticErrorCode.SERVICE_ERROR,
                original_input=user_input,
                suggestion=f"生成面试题失败: {str(e)}"
            )
        
        # 4. 落库
        try:
            topic = await self.save_topic(topic_data)
        except Exception as e:
            return error_result(
                error_code=SemanticErrorCode.SERVICE_ERROR,
                original_input=user_input,
                suggestion=f"落库失败: {str(e)}"
            )
        
        # 5. 发送消息到向量队列
        try:
            await self.db_service.send_single_to_embedding_queue(topic.topic)
        except Exception as e:
            print(f"[Warning] 发送向量队列消息失败: {str(e)}")
        
        return SemanticResult(
            success=True,
            code="SEM_0000",
            message="Topic 创建成功",
            data={
                "topic_id": str(topic.id),
                "topic_name": topic.topic,
                "domain": topic.domain,
                "difficulty": topic.difficulty,
            },
            original_input=user_input,
        )


# 同步版本的完整流程（用于 if __main__ 测试）
def get_topic_flow_sync(user_input: str) -> dict:
    """
    同步版本：完整流程（不含落库）
    用于测试时快速验证语义转换和生成功能
    """
    llm_service = TopicLLMService()
    
    # 1. 语义转换
    print(f"\n[Step 1] 语义转换: {user_input}")
    trans_result = semantic_convert(user_input)
    
    if not trans_result.success:
        print(f"  [Failed] {trans_result.code}: {trans_result.error.message if trans_result.error else ''}")
        return {"success": False, "step": "semantic_trans", "error": trans_result.error.message if trans_result.error else str(trans_result)}
    
    semantic_data = trans_result.data
    print(f"  [Success] 标准化输出: {semantic_data.standardized_output[:50]}...")
    
    # 2. 生成面试题
    print(f"\n[Step 2] 生成面试题...")
    try:
        topic_data = llm_service.generate_topic(semantic_data.standardized_output)
        print(f"  [Success] 生成完成，包含 keys: {list(topic_data.keys())}")
        return {
            "success": True,
            "semantic_result": {
                "standardized_output": semantic_data.standardized_output,
                "confidence": semantic_data.confidence,
            },
            "topic_data": topic_data,
        }
    except Exception as e:
        print(f"  [Failed] {str(e)}")
        return {"success": False, "step": "generate_topic", "error": str(e)}


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    load_dotenv(env_path)
    
    print("=== Topic 获取服务测试 ===")
    print(f"API_MODEL: {os.getenv('API_MODEL')}")
    
    test_cases = [
        "HashMap底层实现",
        "Python装饰器原理",
    ]
    
    for user_input in test_cases:
        print(f"\n{'='*50}")
        result = get_topic_flow_sync(user_input)
        
        if result["success"]:
            print(f"\n[Final Result] 成功!")
            print(f"  标准化输出: {result['semantic_result']['standardized_output']}")
            print(f"  置信度: {result['semantic_result']['confidence']}")
            print(f"  生成数据 keys: {list(result['topic_data'].keys())}")
        else:
            print(f"\n[Final Result] 失败!")
            print(f"  失败步骤: {result['step']}")
            print(f"  错误信息: {result['error']}")
    
    print(f"\n{'='*50}")
    print("=== 测试完成 ===")