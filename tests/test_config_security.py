"""R-005 生产配置启动护栏。"""
import pytest
from pydantic import ValidationError

from src.config.settings import Settings

pytestmark = [pytest.mark.unit, pytest.mark.security]


def test_production_rejects_placeholders():
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production", JWT_SECRET="change-me" * 5,
            DATABASE_URL="postgres://app:change_me@db/topic",
        )


def test_production_accepts_explicit_secrets():
    settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET="x" * 40,
        DATABASE_URL="postgres://app:strong@app-db/topic",
        DATABASE_READ_URL="postgres://reader:strong@app-db/topic",
        TS_DS_APIKEY="sk-live-value",
        EMBEDDING_API_KEY="embedding-live-value",
        RABBITMQ_PASSWORD="rabbit-strong-value",
        SMTP_USER="mailer@example.org",
        SMTP_PASS="smtp-strong-value",
    )
    assert settings.ENVIRONMENT == "production"
