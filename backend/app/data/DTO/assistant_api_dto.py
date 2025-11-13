from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.data.DTO.message_flow_dto import AssistantAnswer, UserMessageRequest


class AssistantMessageRequest(UserMessageRequest):
    """Inbound payload for the assistant message endpoint."""


class AssistantMessageResponse(BaseModel):
    """Response payload after the assistant processes a message."""

    session_id: UUID
    user_message_id: UUID
    assistant_message_id: Optional[UUID] = None  # None when form dismissed without creating message
    answer: AssistantAnswer
    form_id: Optional[UUID] = None


class ConversationSessionRead(BaseModel):
    """Lightweight view of a conversation session for list endpoints."""

    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    ended_at: Optional[datetime] = None
    feedback_rating: Optional[int] = None


class ConversationMessageRead(BaseModel):
    """Serializable view of a stored conversation message."""

    id: UUID
    session_id: UUID
    role: str
    content: str
    message_metadata: dict = Field(default_factory=dict)
    created_at: datetime
    helpful: Optional[bool] = None


class ConversationHistoryResponse(BaseModel):
    """Bundle of a session and its recent messages."""

    session: ConversationSessionRead
    history: List[ConversationMessageRead] = Field(default_factory=list)


class SessionFeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
