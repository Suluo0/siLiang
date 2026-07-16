from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    ENVIRONMENT: str = "development"
    JWT_SECRET: str = ""

    # ── Database ──
    DATABASE_URL: str = ""
    DATABASE_READ_URL: str = ""

    # ── Milvus ──
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "topic_embeddings"

    # ── Embedding ──
    EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"
    EMBEDDING_API_URL: str = "https://api.siliconflow.cn/v1/embeddings"
    EMBEDDING_API_KEY: str = ""
    TS_DS_APIKEY: str = ""

    # ── Tracing ──
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # ── RabbitMQ ──
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"

    SMTP_USER: str = ""
    SMTP_PASS: str = ""

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.ENVIRONMENT.lower() not in {"production", "prod"}:
            return self
        required = {
            "JWT_SECRET": self.JWT_SECRET,
            "DATABASE_URL": self.DATABASE_URL,
            "DATABASE_READ_URL": self.DATABASE_READ_URL,
            "TS_DS_APIKEY": self.TS_DS_APIKEY,
            "EMBEDDING_API_KEY": self.EMBEDDING_API_KEY,
            "RABBITMQ_PASSWORD": self.RABBITMQ_PASSWORD,
            "SMTP_USER": self.SMTP_USER,
            "SMTP_PASS": self.SMTP_PASS,
        }
        placeholders = ("replace_with", "change_me", "change-me", "your-")
        invalid = [
            name for name, value in required.items()
            if not value.strip() or any(marker in value.lower() for marker in placeholders)
        ]
        if len(self.JWT_SECRET) < 32:
            invalid.append("JWT_SECRET")
        if self.RABBITMQ_PASSWORD == "guest":
            invalid.append("RABBITMQ_PASSWORD")
        if invalid:
            raise ValueError(f"production configuration is missing secure values: {', '.join(sorted(set(invalid)))}")
        return self


settings = Settings()
