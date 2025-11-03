from __future__ import annotations

import os

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "backend"
    secret_key: str
    database_url: str
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    OPENAI_API_KEY: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    OPENAI_VISION_MODEL: str = Field(default_factory=lambda: os.getenv("MODEL_VISION", "gpt-4o-mini"))
    ALLOWED_TYPES: set[str] = {"image/jpeg", "image/png", "image/webp"}
    MAX_IMAGE_BYTES: int = 8 * 1024 * 1024  # 8MB
    LABELS: list[str] = ["dirty", "spots", "residue", "cloudy_glass", "greasy"]
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
