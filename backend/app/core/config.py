from __future__ import annotations

import json
import os

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "backend"
    secret_key: str
    database_url: str
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    OPENAI_API_KEY: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    OPENAI_RESPONSE_MODEL: str = Field(
        default_factory=lambda: os.getenv("MODEL_RESPONSE", os.getenv("OPENAI_RESPONSE_MODEL", "gpt-5-mini")),
        description="Primary text responses model identifier.",
    )
    OPENAI_VISION_MODEL: str = Field(
        default_factory=lambda: os.getenv("MODEL_VISION", os.getenv("OPENAI_VISION_MODEL", "gpt-5-mini")),
        description="Vision-capable model identifier for image analysis.",
    )
    openai_pricing: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        alias="OPENAI_PRICING",
        description="Mapping of model pricing overrides keyed by model name or prefix. Values should be per-1M token costs with 'input' and 'output' keys.",
    )
    ALLOWED_TYPES: set[str] = {"image/jpeg", "image/png", "image/webp"}
    MAX_IMAGE_BYTES: int = 8 * 1024 * 1024  # 8MB
    LABELS: list[str] = ["dirty", "spots", "residue", "cloudy_glass", "greasy"]
    cors_origins: list[str] = Field(
        alias="cors_origins_default",
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    cors_origins_csv: str | None = Field(default=None, alias="CORS_ORIGINS", validation_alias="CORS_ORIGINS")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def apply_cors_csv(self) -> "Settings":
        if isinstance(self.cors_origins_csv, str) and self.cors_origins_csv.strip():
            self.cors_origins = [origin.strip() for origin in self.cors_origins_csv.split(",") if origin.strip()]
        return self

    @field_validator("openai_pricing", mode="before")
    @classmethod
    def parse_openai_pricing(cls, value: object) -> dict[str, dict[str, float]]:
        if value in (None, "", {}):
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:  # noqa: F841
                raise ValueError("OPENAI_PRICING must be valid JSON") from exc
            if isinstance(parsed, dict):
                return parsed
            raise ValueError("OPENAI_PRICING JSON must decode to an object with model pricing data")
        raise TypeError("OPENAI_PRICING must be provided as a JSON string or dict")


settings = Settings()
