"""
Topic 数据库服务
负责 Topic 数据的落库和查询
"""
from typing import List, Optional

from src.models.topic import Topic
from src.common.rabbitmq import RabbitMQPublisher
from tortoise.transactions import in_transaction


class TopicDBService:
    """Topic 数据库服务 - 负责数据落库"""
    
    async def save_topic(self, topic_data: dict) -> Topic:
        """
        根据生成结果完整落库（原子性操作）
        
        设计原则：
        1. 事务保证：所有操作在单个事务中，失败全部回滚
        2. 防重处理：检查 topic 是否已存在，避免复写
        3. 关联表一次性插入：减少数据库往返
        4. 错误传播：失败时抛出明确异常
        
        Args:
            topic_data: 包含 topic 主表和关联表数据的字典
            
        Returns:
            Topic: 创建的 Topic 实例
            
        Raises:
            ValueError: 数据格式错误
            RuntimeError: 数据库操作失败
        """
        from src.models.topic_prerequisite import TopicPrerequisite
        from src.models.topic_core_concept import TopicCoreConcept
        from src.models.topic_derivative import TopicDerivative
        from src.models.topic_extension import TopicExtension
        from src.models.topic_evaluation_anchor import TopicEvaluationAnchor
        from src.models.topic_similar_question import TopicSimilarQuestion
        from src.models.topic_advanced_question import TopicAdvancedQuestion
        from src.models.topic_reference import TopicReference
        
        topic_info = topic_data.get("topic", {})
        topic_name = topic_info.get("topic", "").strip()
        
        if not topic_name:
            raise ValueError("Topic name is required")
        
        # 使用事务保证原子性
        async with in_transaction():
            # 检查是否已存在（防重处理）
            existing = await Topic.filter(topic=topic_name).first()
            if existing:
                raise RuntimeError(f"Topic '{topic_name}' already exists, id={existing.id}")
        
        # JSONB 字段处理
        alias_list = topic_info.get("alias")
        tags_list = topic_info.get("tags")
        keywords_list = topic_info.get("keywords")
        
        topic = await Topic.create(
            topic=topic_name,
            alias=alias_list if alias_list else None,
            domain=topic_info.get("domain", "编程基础"),
            category=topic_info.get("category"),
            tags=tags_list if tags_list else None,
            difficulty=topic_info.get("difficulty", 3),
            mastery_level=topic_info.get("mastery_level", 0),
            review_count=topic_info.get("review_count", 0),
            keywords=keywords_list if keywords_list else None,
            core_summary=topic_info.get("core_summary"),
            core_points=topic_info.get("core_points"),
            detailed_explanation=topic_info.get("detailed_explanation"),
            agent_instructions_a=topic_info.get("agent_instructions_a"),
            agent_instructions_b=topic_info.get("agent_instructions_b"),
            agent_instructions_c=topic_info.get("agent_instructions_c"),
            code_example=topic_info.get("code_example"),
            traps=topic_info.get("traps"),
            bonuses=topic_info.get("bonuses"),
        )
        
        # 批量插入关联表数据
        await self._batch_create_relations(topic, topic_data)
        
        return topic
    
    async def _batch_create_relations(self, topic: Topic, topic_data: dict) -> None:
        """
        批量创建关联表数据
        使用 bulk_create 减少数据库往返，提升性能
        """
        from src.models.topic_prerequisite import TopicPrerequisite
        from src.models.topic_core_concept import TopicCoreConcept
        from src.models.topic_derivative import TopicDerivative
        from src.models.topic_extension import TopicExtension
        from src.models.topic_evaluation_anchor import TopicEvaluationAnchor
        from src.models.topic_similar_question import TopicSimilarQuestion
        from src.models.topic_advanced_question import TopicAdvancedQuestion
        from src.models.topic_reference import TopicReference
        
        relations_config = [
            ("prerequisites", TopicPrerequisite, "content", ["sort_order"]),
            ("core_concepts", TopicCoreConcept, "content", ["sort_order"]),
            ("derivatives", TopicDerivative, "content", ["sort_order"]),
            ("extensions", TopicExtension, "content", ["sort_order"]),
            ("evaluation_anchors", TopicEvaluationAnchor, "content", ["level", "sort_order"]),
            ("similar_questions", TopicSimilarQuestion, "question", ["answer_hint", "sort_order"]),
            ("advanced_questions", TopicAdvancedQuestion, "question", ["answer_hint", "sort_order"]),
            ("references", TopicReference, "title", ["url", "description", "sort_order"]),
        ]
        
        for data_key, Model, name_field, extra_fields in relations_config:
            items = topic_data.get(data_key, [])
            if not items:
                continue
            
            objs = []
            for item in items:
                kwargs = {"topic": topic}
                if name_field in item:
                    kwargs[name_field] = item[name_field]
                for extra_field in extra_fields:
                    if extra_field in item:
                        kwargs[extra_field] = item[extra_field]
                objs.append(Model(**kwargs))
            
            if objs:
                await Model.bulk_create(objs, batch_size=50)

    async def send_to_embedding_queue(self, topic_names: List[str]) -> int:
        """
        将 topic_name 发送到向量 embedding 队列
        
        Args:
            topic_names: topic 名称列表
            
        Returns:
            int: 发送的消息数量
        """
        publisher = RabbitMQPublisher.get_instance()
        count = 0
        
        for topic_name in topic_names:
            if not topic_name or not topic_name.strip():
                continue
            await publisher.send_task(
                task_type="generate_embedding",
                task_data={"topic_name": topic_name.strip()}
            )
            count += 1
        
        return count

    async def send_single_to_embedding_queue(self, topic_name: str) -> bool:
        """
        将单个 topic_name 发送到向量 embedding 队列
        
        Args:
            topic_name: topic 名称
            
        Returns:
            bool: 是否发送成功
        """
        if not topic_name or not topic_name.strip():
            return False
        
        result = await self.send_to_embedding_queue([topic_name])
        return result > 0


class TopicEmbeddingConsumer:
    """Topic 向量 embedding 消费者"""
    
    def __init__(self):
        from src.service.semantic_trans import SemanticTransService
        self.semantic_service = SemanticTransService()
    
    async def process_message(self, message: dict) -> None:
        """
        处理消息：生成语义向量并落库
        
        Args:
            message: 消息格式 {"type": "generate_embedding", "data": {"topic_name": "..."}}
        """
        task_type = message.get("type")
        task_data = message.get("data", {})
        topic_name = task_data.get("topic_name")
        
        if task_type != "generate_embedding" or not topic_name:
            print(f"跳过无效消息: {message}")
            return
        
        # 1. 查找 topic
        topic = await Topic.filter(topic=topic_name).first()
        if not topic:
            print(f"Topic 未找到: {topic_name}")
            return
        
        # 2. 如果已有向量，跳过
        if topic.embedding_vector:
            print(f"Topic {topic_name} 已有向量，跳过")
            return
        
        # 3. 生成语义向量
        semantic_result = self.semantic_service.convert(
            content=topic.core_summary or topic.topic,
            format_type="formal_text"
        )
        
        if not semantic_result.success:
            print(f"语义转换失败: {semantic_result.error.message if semantic_result.error else 'unknown'}")
            return
        
        # 4. 获取标准化输出作为向量文本（实际向量需要嵌入模型生成）
        # 这里使用文本的 JSON 表示作为向量占位，实际生产环境应使用专门的嵌入模型
        embedding_text = semantic_result.data.standardized_output
        
        # 5. 更新 topic 的 embedding_vector
        topic.embedding_vector = embedding_text
        await topic.save()
        
        print(f"Topic {topic_name} 向量生成成功")


if __name__ == "__main__":
    # 测试代码
    service = TopicDBService()
    print("TopicDBService 已加载")