"""
RabbitMQ 通用工具
提供生产和消费的通用方法
"""
import json
import asyncio
from typing import Callable, Any, Optional
from functools import wraps

import aio_pika
from aio_pika import Message, DeliveryMode
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractQueue, AbstractIncomingMessage

from src.config.rabbitmq_config import rabbitmq_config


def async_retry(max_retries: int = 3, delay: float = 1.0):
    """异步重试装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for i in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if i < max_retries - 1:
                        await asyncio.sleep(delay * (i + 1))
            raise last_exception
        return wrapper
    return decorator


class RabbitMQClient:
    """RabbitMQ 通用客户端"""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        vhost: Optional[str] = None,
        queue_name: Optional[str] = None,
        exchange_name: Optional[str] = None,
    ):
        self.config = {
            "host": host or rabbitmq_config.host,
            "port": port or rabbitmq_config.port,
            "username": username or rabbitmq_config.username,
            "password": password or rabbitmq_config.password,
            "vhost": vhost or rabbitmq_config.vhost,
            "queue_name": queue_name or rabbitmq_config.queue_name,
            "exchange_name": exchange_name or rabbitmq_config.exchange_name,
        }
        self._connection: Optional[AbstractConnection] = None
        self._channel: Optional[AbstractChannel] = None
        self._queue: Optional[AbstractQueue] = None
        self._exchange = None
    
    @property
    def url(self) -> str:
        return f"amqp://{self.config['username']}:{self.config['password']}@{self.config['host']}:{self.config['port']}/{self.config['vhost']}"
    
    @async_retry(max_retries=3, delay=1.0)
    async def connect(self) -> None:
        """建立连接（带重试）"""
        if self._connection and not self._connection.is_closed:
            return
        
        self._connection = await aio_pika.connect_robust(self.url)
        self._channel = await self._connection.channel()
        
        # 设置 QoS
        await self._channel.set_qos(prefetch_count=10)
        
        # 声明交换机
        self._exchange = await self._channel.declare_exchange(
            self.config["exchange_name"],
            aio_pika.ExchangeType.DIRECT,
            durable=True
        )
        
        # 声明队列
        self._queue = await self._channel.declare_queue(
            self.config["queue_name"],
            durable=True
        )
        
        # 绑定队列到交换机
        await self._queue.bind(self._exchange, routing_key=self.config["queue_name"])
    
    async def disconnect(self) -> None:
        """断开连接"""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        self._connection = None
        self._channel = None
        self._queue = None
        self._exchange = None
    
    async def publish(self, data: dict, routing_key: Optional[str] = None) -> None:
        """
        发布消息
        
        Args:
            data: 消息数据（会被序列化为 JSON）
            routing_key: 路由键，默认使用队列名
        """
        if not self._channel:
            await self.connect()
        
        message = Message(
            body=json.dumps(data, ensure_ascii=False).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json"
        )
        
        key = routing_key or self.config["queue_name"]
        await self._exchange.publish(message, routing_key=key)
    
    async def publish_raw(self, body: bytes, routing_key: Optional[str] = None) -> None:
        """
        发布原始字节消息
        
        Args:
            body: 原始字节数据
            routing_key: 路由键
        """
        if not self._channel:
            await self.connect()
        
        message = Message(
            body=body,
            delivery_mode=DeliveryMode.PERSISTENT
        )
        
        key = routing_key or self.config["queue_name"]
        await self._exchange.publish(message, routing_key=key)
    
    async def consume(
        self,
        callback: Callable[[dict], Any],
        auto_ack: bool = False
    ) -> None:
        """
        消费消息
        
        Args:
            callback: 处理消息的回调函数，接收 dict 类型参数
            auto_ack: 是否自动确认
        """
        if not self._queue:
            await self.connect()
        
        async def process_message(message: AbstractIncomingMessage) -> None:
            if not auto_ack:
                async with message.process():
                    try:
                        data = json.loads(message.body.decode())
                        await callback(data)
                    except json.JSONDecodeError:
                        # 非 JSON 格式，当作原始字节处理
                        await callback(message.body.decode())
                    except Exception as e:
                        print(f"消息处理失败: {e}")
                        raise
            else:
                try:
                    data = json.loads(message.body.decode())
                    await callback(data)
                except json.JSONDecodeError:
                    await callback(message.body.decode())
                except Exception as e:
                    print(f"消息处理失败: {e}")
        
        await self._queue.consume(process_message)
    
    async def get(self, timeout: float = 1.0) -> Optional[dict]:
        """
        获取单条消息（非阻塞）
        
        Args:
            timeout: 等待超时时间
            
        Returns:
            消息数据或 None
        """
        if not self._queue:
            await self.connect()
        
        try:
            message = await self._queue.get(timeout=timeout, fail=True)
            async with message.process():
                return json.loads(message.body.decode())
        except asyncio.TimeoutError:
            return None
        except Exception:
            return None


class RabbitMQPublisher:
    """RabbitMQ 生产者工具类"""
    
    _instance: Optional["RabbitMQPublisher"] = None
    
    def __init__(self):
        self._client = RabbitMQClient()
    
    @classmethod
    def get_instance(cls) -> "RabbitMQPublisher":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def send_task(self, task_type: str, task_data: dict) -> None:
        """发送任务消息"""
        await self._client.publish({
            "type": task_type,
            "data": task_data
        })
    
    async def send_message(self, message: dict) -> None:
        """发送通用消息"""
        await self._client.publish(message)


class RabbitMQConsumer:
    """RabbitMQ 消费者工具类"""
    
    def __init__(self, queue_name: Optional[str] = None):
        self._client = RabbitMQClient(queue_name=queue_name)
        self._running = False
    
    async def start(self, callback: Callable[[dict], Any]) -> None:
        """启动消费者"""
        self._running = True
        await self._client.consume(callback)
        
        # 保持运行
        while self._running:
            await asyncio.sleep(1)
    
    async def stop(self) -> None:
        """停止消费者"""
        self._running = False
        await self._client.disconnect()


# 全局 publisher 实例
rabbitmq_publisher = RabbitMQPublisher.get_instance()


if __name__ == "__main__":
    async def test_producer():
        """测试生产者"""
        publisher = RabbitMQPublisher.get_instance()
        
        await publisher.send_task("test_task", {"name": "测试", "value": 123})
        print("消息已发送")
    
    async def test_consumer():
        """测试消费者"""
        async def handle_message(data: dict):
            print(f"收到消息: {data}")
        
        consumer = RabbitMQConsumer()
        await consumer.start(handle_message)
    
    # 根据参数决定运行测试
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "consumer":
        asyncio.run(test_consumer())
    else:
        asyncio.run(test_producer())