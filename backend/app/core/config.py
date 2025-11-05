from __future__ import annotations

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
    OPENAI_VISION_MODEL: str = Field(default_factory=lambda: os.getenv("MODEL_VISION", "gpt-4o-mini"))
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
    chroma_url: str | None = Field(default=None, alias="CHROMA_URL")
    chroma_path: str = Field(default=".chroma", alias="CHROMA_PATH")
    chroma_collection: str = Field(default="troubleshoot-cases", alias="CHROMA_COLLECTION")
    chroma_auto_seed: bool = Field(default=True, alias="CHROMA_AUTO_SEED")
    knowledge_file: str = Field(default="app/data/troubleshoot_map.json", alias="KNOWLEDGE_FILE")

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


settings = Settings()
