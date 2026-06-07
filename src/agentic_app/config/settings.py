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


# Required fields are populated from the environment / .env at runtime by
# pydantic-settings, so the no-arg construction is valid despite mypy's view.
settings = Settings()  # type: ignore[call-arg]
