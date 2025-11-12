"""Knowledge and tool result DTOs."""
from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field


class AssistantToolResult(BaseModel):
    """The result of executing an assistant tool."""

    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
