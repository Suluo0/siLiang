"""
项目配置
从环境变量读取配置
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    DATABASE_URL: str

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


setting = Settings()
