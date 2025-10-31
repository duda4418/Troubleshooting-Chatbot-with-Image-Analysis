from __future__ import annotations

from typing import List
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationAIContext(BaseModel):
    session_id: UUID
    events: List[str] = Field(default_factory=list)
