"""
Alerting service configuration.
"""

import os
from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_file() -> str:
    """
    Determine which .env file to load based on ENVIRONMENT.
    """
    env = os.getenv("ENVIRONMENT", "development")
    mapping = {
        "production": ".env",
        "development": ".env.dev",
    }
    env_file = mapping.get(env, ".env.dev")
    load_dotenv(env_file, override=True)
    return env_file


class Settings(BaseSettings):
    """Configuration settings for the alerting service."""

    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: Literal["development", "production"] = "development"

    DOMAIN: str = "0.0.0.0"
    DEBUG_MODE: bool = False

    # Redis for suppression & caching
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))

    # SMTP settings for email notifications
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.example.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "alerts@example.com")

    ALERTING_HOST: str = os.getenv("ALERTING_HOST", "alert")
    ALERTING_PORT: int = int(os.getenv("ALERTING_PORT", "8001"))


@lru_cache()
def get_settings() -> Settings:
    """Get (and cache) the Settings instance."""
    return Settings()
