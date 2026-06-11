"""
RabbitMQ 配置
"""
import os
from pydantic_settings import BaseSettings


class RabbitMQSettings(BaseSettings):
    """RabbitMQ 配置"""
    
    # 连接地址
    host: str = "localhost"
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    vhost: str = "/"
    
    # 队列配置
    queue_name: str = "topic_tasks"
    exchange_name: str = "topic_exchange"
    
    @property
    def url(self) -> str:
        """生成 AMQP URL"""
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/{self.vhost}"
    
    class Config:
        env_file = ".env"
        env_prefix = "RABBITMQ_"
        extra = "ignore"


# 全局配置实例
rabbitmq_config = RabbitMQSettings()