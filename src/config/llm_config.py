"""
LLM 配置管理
统一管理各个模型的配置
"""
import os
from typing import Optional, Dict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class ModelConfig(BaseModel):
    """模型配置"""
    name: str = Field(description="模型名称")
    temperature: float = Field(default=0.2, description="采样随机性")
    max_tokens: int = Field(default=2048, description="最大输出 token 数")
    timeout: int = Field(default=30, description="超时时间(秒)")
    max_retries: int = Field(default=2, description="最大重试次数")
    api_key: Optional[str] = Field(default=None, description="API 密钥")
    base_url: Optional[str] = Field(default=None, description="API 地址")


class LLMConfig:
    """LLM 配置管理类"""
    
    # 默认配置（从环境变量读取）
    DEFAULT_MODEL = os.getenv("API_MODEL", "gpt-4-turbo")
    DEFAULT_API_KEY = os.getenv("API_SECRET") or os.getenv("API_SCRECT")
    DEFAULT_BASE_URL = os.getenv("API_ADDRESS")
    
    # 预定义模型配置
    MODELS: Dict[str, ModelConfig] = {
        "MiniMax-M2.7": ModelConfig(
            name="MiniMax-M2.7",
            temperature=0.7,
            max_tokens=4096,
            timeout=120,
            max_retries=3,
            api_key=DEFAULT_API_KEY,
            base_url=DEFAULT_BASE_URL,
        ),
        "gpt-4-turbo": ModelConfig(
            name="gpt-4-turbo",
            temperature=0.2,
            max_tokens=2048,
            timeout=30,
            max_retries=2,
        ),
        "gpt-4o": ModelConfig(
            name="gpt-4o",
            temperature=0.2,
            max_tokens=4096,
            timeout=30,
            max_retries=2,
        ),
        "gpt-3.5-turbo": ModelConfig(
            name="gpt-3.5-turbo",
            temperature=0.3,
            max_tokens=2048,
            timeout=30,
            max_retries=2,
        ),
    }
    
    @classmethod
    def get_model_config(cls, model_name: Optional[str] = None) -> ModelConfig:
        """获取模型配置"""
        if model_name is None:
            model_name = cls.DEFAULT_MODEL
        
        if model_name in cls.MODELS:
            config = cls.MODELS[model_name].model_copy(deep=True)
            if config.api_key is None:
                config.api_key = cls.DEFAULT_API_KEY
            if config.base_url is None:
                config.base_url = cls.DEFAULT_BASE_URL
            return config
        
        return ModelConfig(
            name=model_name,
            api_key=cls.DEFAULT_API_KEY,
            base_url=cls.DEFAULT_BASE_URL,
        )
    
    @classmethod
    def register_model(cls, model_config: ModelConfig) -> None:
        """注册新模型"""
        cls.MODELS[model_config.name] = model_config
    
    @classmethod
    def list_models(cls) -> list:
        """列出所有可用模型"""
        return list(cls.MODELS.keys())


def get_model_config(model_name: Optional[str] = None) -> ModelConfig:
    """获取模型配置的便捷函数"""
    return LLMConfig.get_model_config(model_name)


def list_available_models() -> list:
    """列出所有可用模型"""
    return LLMConfig.list_models()
