from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class KnowledgeHit(BaseModel):
    label: str
    similarity: float
    summary: str
    steps: List[str] = Field(default_factory=list)


class AssistantToolResult(BaseModel):
    tool_name: str
    success: bool
    details: Dict[str, Any] = Field(default_factory=dict)
