from __future__ import annotations

from datetime import datetime
from typing import Optional
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, Enum as SAEnum, UniqueConstraint
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


class FormStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    REJECTED = "rejected"


class FormInputType(str, Enum):
    YES_NO = "yes_no"
    TEXT = "text"
    SINGLE_CHOICE = "single_choice"


class ConversationForm(SQLModel, table=True):
    """Dynamic form attached to a conversation session."""

    __tablename__ = "conversation_form"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    session_id: UUID = Field(foreign_key="conversation_session.id", nullable=False, index=True)
    title: Optional[str] = Field(default=None, nullable=True, max_length=120)
    description: Optional[str] = Field(default=None, nullable=True)
    status: FormStatus = Field(
        default=FormStatus.IN_PROGRESS,
        sa_column=Column(SAEnum(FormStatus, name="form_status_enum"), nullable=False),
    )
    rejection_reason: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    submitted_at: Optional[datetime] = Field(default=None, nullable=True)
    rejected_at: Optional[datetime] = Field(default=None, nullable=True)


class ConversationFormField(SQLModel, table=True):
    """Individual question/input for a dynamic conversation form."""

    __tablename__ = "conversation_form_field"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    form_id: UUID = Field(foreign_key="conversation_form.id", nullable=False, index=True)
    prompt: str = Field(nullable=False, max_length=512)
    input_type: FormInputType = Field(
        default=FormInputType.TEXT,
        sa_column=Column(SAEnum(FormInputType, name="form_input_type_enum"), nullable=False),
    )
    required: bool = Field(default=True, nullable=False)
    position: int = Field(default=0, nullable=False)
    placeholder: Optional[str] = Field(default=None, nullable=True, max_length=256)
    created_at: datetime = Field(default_factory=utcnow)


class ConversationFormFieldOption(SQLModel, table=True):
    """Selectable option for single-choice form fields."""

    __tablename__ = "conversation_form_field_option"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    field_id: UUID = Field(foreign_key="conversation_form_field.id", nullable=False, index=True)
    value: str = Field(nullable=False, max_length=128)
    label: str = Field(nullable=False, max_length=128)
    position: int = Field(default=0, nullable=False)
    created_at: datetime = Field(default_factory=utcnow)


class ConversationFormResponse(SQLModel, table=True):
    """User-provided answer for a specific form field."""

    __tablename__ = "conversation_form_response"
    __table_args__ = (
        UniqueConstraint("form_id", "field_id", name="uq_conversation_form_response"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    form_id: UUID = Field(foreign_key="conversation_form.id", nullable=False, index=True)
    field_id: UUID = Field(foreign_key="conversation_form_field.id", nullable=False, index=True)
    selected_option_id: Optional[UUID] = Field(foreign_key="conversation_form_field_option.id", default=None, nullable=True, index=True)
    value: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

