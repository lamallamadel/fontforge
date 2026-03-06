"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the AIFont API server."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ------------------------------------------------------------------ #
    # Database                                                             #
    # ------------------------------------------------------------------ #
    database_url: str = "postgresql+asyncpg://aifont:aifont@localhost:5432/aifont"

    # ------------------------------------------------------------------ #
    # Redis / Celery                                                       #
    # ------------------------------------------------------------------ #
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ------------------------------------------------------------------ #
    # JWT / Auth                                                           #
    # ------------------------------------------------------------------ #
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # ------------------------------------------------------------------ #
    # Rate limiting                                                        #
    # ------------------------------------------------------------------ #
    rate_limit_per_minute: int = 60

    # ------------------------------------------------------------------ #
    # Upload                                                               #
    # ------------------------------------------------------------------ #
    max_upload_size_bytes: int = 50 * 1024 * 1024  # 50 MB
    allowed_font_extensions: list[str] = [".otf", ".ttf", ".woff", ".woff2", ".sfd"]
    allowed_svg_extensions: list[str] = [".svg"]

    # ------------------------------------------------------------------ #
    # General                                                              #
    # ------------------------------------------------------------------ #
    app_title: str = "AIFont API"
    app_version: str = "0.1.0"
    debug: bool = False

    @field_validator("secret_key")
    @classmethod
    def _secret_not_empty(cls, v: str) -> str:  # noqa: N805
        if not v:
            raise ValueError("secret_key must not be empty")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
