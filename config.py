import os
from pydantic import BaseModel, Field

class Settings(BaseModel):
    OPENAI_API_KEY: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    OPENAI_VISION_MODEL: str = Field(default_factory=lambda: os.getenv("MODEL_VISION", "gpt-4o-mini"))
    OPENAI_TEXT_MODEL: str = Field(default_factory=lambda: os.getenv("MODEL_TEXT", "gpt-4o-mini"))
    ALLOWED_TYPES: set[str] = {"image/jpeg", "image/png", "image/webp"}
    MAX_IMAGE_BYTES: int = 8 * 1024 * 1024  # 8MB
    LABELS: list[str] = ["dirty", "spots", "residue", "cloudy_glass", "greasy"]
    FALLBACK: str = "inconclusive"

settings = Settings()

if not settings.OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in env")
