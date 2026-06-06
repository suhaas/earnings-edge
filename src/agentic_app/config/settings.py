"""Configuration and settings management."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    anthropic_api_key: str
    database_url: str
    vectordb_url: str
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()
