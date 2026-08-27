"""Typed application settings."""

from decimal import Decimal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env and environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    llm_provider: str = "groq"
    llm_model: str = "openai/gpt-oss-20b"
    groq_api_key: SecretStr | None = None
    llm_max_tokens: int = 256
    llm_input_rate_per_million: Decimal | None = None
    llm_output_rate_per_million: Decimal | None = None


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
