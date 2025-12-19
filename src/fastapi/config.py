"""FastAPI server configuration."""

import os
from functools import lru_cache
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
from pydantic import AnyUrl, BeforeValidator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_file() -> str:
    """
    Determine the .env file to use.
    You can override this by setting the ENV_FILE environment variable.
    Otherwise, it will choose one based on the ENVIRONMENT value.
    """
    env_file = {
        "production": "../.env",
        "development": "../.env.dev",
    }
    load_dotenv(env_file.get(os.getenv("ENVIRONMENT", "development")), override=True)
    return env_file.get(os.getenv("ENVIRONMENT", "development"), "../.env.dev")


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    """Server config settings."""

    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=True,  # Ensures exact variable name matching
        env_ignore_empty=True,
        extra="ignore",
    )
    ENVIRONMENT: Literal["development", "production"] = "development"
    PROJECT_NAME: str = "Timber Transportation API"

    # API settings
    DOMAIN: str = "0.0.0.0"
    DEBUG_MODE: bool = False
    FASTAPI_API_KEY_HEADER: str = os.getenv("FASTAPI_API_KEY_HEADER", "default_key")
    FASTAPI_API_KEY: str = os.getenv("FASTAPI_API_KEY", "default_key")
    FASTAPI_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = (
        []
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.FASTAPI_CORS_ORIGINS]

    # RabbitMQ settings
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")

    # Redis settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))

    # Database settings
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "default_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "default_password")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "default_db")

    # API settings
    DEVICE_API_URL: str = os.getenv("DEVICE_API_URL", "http://localhost:8000")
    FAULT_API_URL: str = os.getenv("FAULT_API_URL", "http://localhost:8000")

    # Alerting settings
    ALERTING_HOST: str = os.getenv("ALERTING_HOST", "http://localhost")
    ALERTING_PORT: int = int(os.getenv("ALERTING_PORT", "8001"))

    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Ho_Chi_Minh")


# Global settings instance with caching.
@lru_cache()
def get_settings() -> Settings:
    settings = Settings()

    return settings
