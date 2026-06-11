"""
RabbitMQ 服务
提供消息队列连接和发布能力
"""
import json
import asyncio
from typing import Callable, Optional
import aio_pika
from aio_pika import Message, DeliveryMode
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractQueue

from src.config.rabbitmq_config import rabbitmq_config


class RabbitMQService:
    """RabbitMQ 服务类"""
    
    def __init__(self):
        self._connection: Optional[AbstractConnection] = None
        self._channel: Optional[AbstractChannel] = None
        self._queue: Optional[AbstractQueue] = None
    
    async def connect(self) -> None:
        """建立连接"""
        if self._connection and not self._connection.is_closed:
            return
        
        self._connection = await aio_pika.connect_robust(rabbitmq_config.url)
        self._channel = await self._connection.channel()
        
        # 声明交换机
        await self._channel.declare_exchange(
            rabbitmq_config.exchange_name,
            aio_pika.ExchangeType.DIRECT,
            durable=True
        )
        
        # 声明队列
        self._queue = await self._channel.declare_queue(
            rabbitmq_config.queue_name,
            durable=True
        )
        
        # 绑定队列到交换机
        await self._queue.bind(rabbitmq_config.exchange_name, routing_key=rabbitmq_config.queue_name)
    
    async def disconnect(self) -> None:
        """断开连接"""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            self._connection = None
            self._channel = None
            self._queue = None
    
    async def publish(self, data: dict) -> None:
        """
        发布消息到队列
        
        Args:
            data: 要发送的消息数据
        """
        if not self._channel:
            await self.connect()
        
        message = Message(
            body=json.dumps(data, ensure_ascii=False).encode(),
            delivery_mode=DeliveryMode.PERSISTENT
        )
        
        await self._channel.default_exchange.publish(
            message,
            routing_key=rabbitmq_config.queue_name
        )
    
    async def consume(self, callback: Callable) -> None:
        """
        消费消息
        
        Args:
            callback: 处理消息的回调函数，接收 dict 类型参数
        """
        if not self._queue:
            await self.connect()
        
        async def process_message(message: aio_pika.IncomingMessage) -> None:
            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    await callback(data)
                except Exception as e:
                    print(f"消息处理失败: {e}")
        
        await self._queue.consume(process_message)
    
    async def publish_task(self, user_input: str, task_id: str) -> None:
        """
        发布 Topic 生成任务
        
        Args:
            user_input: 用户输入
            task_id: 任务 ID
        """
        await self.publish({
            "type": "generate_topic",
            "user_input": user_input,
            "task_id": task_id
        })


# 全局服务实例
rabbitmq_service = RabbitMQService()


if __name__ == "__main__":
    async def test_publish():
        await rabbitmq_service.connect()
        await rabbitmq_service.publish_task("HashMap底层实现", "test-123")
        print("消息已发送")
        await rabbitmq_service.disconnect()
    
    asyncio.run(test_publish())