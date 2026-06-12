"""
LLM 配置管理 — 单一 LLM 配置来源

所有 LLM 相关配置统一从此处读取，禁止在其他模块中直接 os.getenv()。
"""
import os
from typing import Optional
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    name: str = Field(description="模型名称")
    temperature: float = Field(default=0.2, description="采样随机性")
    max_tokens: int = Field(default=2048, description="最大输出 token 数")
    timeout: int = Field(default=30, description="超时时间(秒)")
    max_retries: int = Field(default=2, description="最大重试次数")
    api_key: Optional[str] = Field(default=None, description="API 密钥")
    base_url: Optional[str] = Field(default=None, description="API 地址")


class LLMConfig:
    """LLM 全局配置 — 所有消费者只从这里取"""

    API_KEY: str = os.getenv("TS_DS_APIKEY", "")
    BASE_URL: str = os.getenv("API_ADDRESS", "https://api.deepseek.com/v1")
    MODEL_NAME: str = os.getenv("API_MODEL", "deepseek-chat")

    _models: dict[str, ModelConfig] = {
        "deepseek-chat": ModelConfig(
            name="deepseek-chat", temperature=0.7, max_tokens=4096,
            timeout=120, max_retries=3),
        "MiniMax-M2.7": ModelConfig(
            name="MiniMax-M2.7", temperature=0.7, max_tokens=4096,
            timeout=120, max_retries=3),
        "gpt-4-turbo": ModelConfig(
            name="gpt-4-turbo", temperature=0.2, max_tokens=2048,
            timeout=30, max_retries=2),
        "gpt-4o": ModelConfig(
            name="gpt-4o", temperature=0.2, max_tokens=4096,
            timeout=30, max_retries=2),
    }

    @classmethod
    def get_model_config(cls, model_name: Optional[str] = None) -> ModelConfig:
        name = model_name or cls.MODEL_NAME
        if name in cls._models:
            cfg = cls._models[name].model_copy(deep=True)
            if cfg.api_key is None:
                cfg.api_key = cls.API_KEY
            if cfg.base_url is None:
                cfg.base_url = cls.BASE_URL
            return cfg
        return ModelConfig(name=name, api_key=cls.API_KEY, base_url=cls.BASE_URL)

    @classmethod
    def register_model(cls, config: ModelConfig) -> None:
        cls._models[config.name] = config

    @classmethod
    def list_models(cls) -> list[str]:
        return list(cls._models.keys())


def get_model_config(model_name: Optional[str] = None) -> ModelConfig:
    return LLMConfig.get_model_config(model_name)


def list_available_models() -> list[str]:
    return LLMConfig.list_models()
