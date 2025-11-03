from __future__ import annotations

from datetime import datetime
from typing import Optional
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Return current UTC timestamp."""
    return datetime.utcnow()


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ConversationSession(SQLModel, table=True):
    """
    Represents a conversation session between a user and the assistant.
    """
    __tablename__ = "conversation_session"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    status: str = Field(default="in_progress", max_length=32)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    ended_at: Optional[datetime] = Field(default=None, nullable=True, description="Timestamp when the session ended.")
    feedback_text: Optional[str] = Field(default=None, nullable=True, description="Free-form user feedback about the overall conversation.")
    feedback_rating: Optional[int] = Field(default=None, nullable=True, description="Optional numeric rating (e.g. 1-5) for the conversation.")



class ConversationMessage(SQLModel, table=True):
    """
    Represents a single message within a conversation session.
    """

    __tablename__ = "conversation_message"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    session_id: UUID = Field(foreign_key="conversation_session.id", nullable=False, index=True)
    role: MessageRole = Field(
        default=MessageRole.USER,
        sa_column=Column(SAEnum(MessageRole, name="message_role_enum"), nullable=False),
    )
    content: str = Field(nullable=False)
    message_metadata: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=True))
    created_at: datetime = Field(default_factory=utcnow)
    helpful: Optional[bool] = Field(default=None, nullable=True, description="User feedback on whether this assistant message was helpful.")


class ConversationImage(SQLModel, table=True):
    """Stores images associated with a conversation (and optionally a specific message) plus AI analysis.

    Keeping images separate avoids bloating message metadata and allows independent lifecycle
    management and re-analysis. Minimal fields for now; can extend later without altering messages.
    """

    __tablename__ = "conversation_image"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    session_id: UUID = Field(foreign_key="conversation_session.id", nullable=False, index=True)
    message_id: Optional[UUID] = Field(foreign_key="conversation_message.id", default=None, nullable=True, index=True)
    original_filename: Optional[str] = Field(default=None, nullable=True, max_length=256)
    storage_uri: str = Field(nullable=False, description="Location of the stored image (path, URI, or key).")
    analysis_text: Optional[str] = Field(default=None, nullable=True, description="AI generated textual description relevant to troubleshooting (e.g., dishwasher).")
    analysis_metadata: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=True), description="Structured analysis output, tags, confidence scores, etc.")
    created_at: datetime = Field(default_factory=utcnow)


