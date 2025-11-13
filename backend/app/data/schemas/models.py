from __future__ import annotations

from datetime import datetime
from typing import Optional
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, Enum as SAEnum, Float, String, Text, UniqueConstraint
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


class SuggestionStatus(str, Enum):
    SUGGESTED = "suggested"
    COMPLETED = "completed"
    NOT_HELPFUL = "not_helpful"
    ESCALATED = "escalated"


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


class ModelUsageLog(SQLModel, table=True):
    """Stores per-response model usage metrics to power cost dashboards."""

    __tablename__ = "model_usage_log"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    session_id: UUID = Field(foreign_key="conversation_session.id", nullable=False, index=True)
    message_id: Optional[UUID] = Field(foreign_key="conversation_message.id", default=None, nullable=True, index=True)
    request_type: str = Field(
        default="response_generation",
        sa_column=Column(String(length=64), nullable=False),
    )
    model: str = Field(
        default="",
        sa_column=Column(String(length=128), nullable=False),
    )
    input_tokens: int = Field(default=0, nullable=False)
    output_tokens: int = Field(default=0, nullable=False)
    total_tokens: int = Field(default=0, nullable=False)
    cost_input: float = Field(default=0.0, sa_column=Column(Float, nullable=False))
    cost_output: float = Field(default=0.0, sa_column=Column(Float, nullable=False))
    cost_total: float = Field(default=0.0, sa_column=Column(Float, nullable=False))
    usage_metadata: dict = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=True),
        description="Raw usage payload and pricing hints for auditability.",
    )
    created_at: datetime = Field(default_factory=utcnow)


class ProblemCategory(SQLModel, table=True):
    __tablename__ = "problem_category"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    slug: str = Field(
        sa_column=Column(String(length=64), nullable=False, unique=True),
        description="Stable identifier for referencing this category.",
    )
    name: str = Field(sa_column=Column(String(length=128), nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))


class ProblemCause(SQLModel, table=True):
    __tablename__ = "problem_cause"
    __table_args__ = (
        UniqueConstraint("category_id", "slug", name="uq_problem_cause_category_slug"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    category_id: UUID = Field(foreign_key="problem_category.id", nullable=False, index=True)
    slug: str = Field(sa_column=Column(String(length=64), nullable=False))
    name: str = Field(sa_column=Column(String(length=128), nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    detection_hints: list[str] = Field(default_factory=list, sa_column=Column(JSONB, nullable=True))
    default_priority: int = Field(default=0, nullable=False)


class ProblemSolution(SQLModel, table=True):
    __tablename__ = "problem_solution"
    __table_args__ = (
        UniqueConstraint("cause_id", "slug", name="uq_problem_solution_cause_slug"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    cause_id: UUID = Field(foreign_key="problem_cause.id", nullable=False, index=True)
    slug: str = Field(sa_column=Column(String(length=64), nullable=False))
    title: str = Field(sa_column=Column(String(length=160), nullable=False))
    summary: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    instructions: str = Field(sa_column=Column(Text, nullable=False))
    step_order: int = Field(default=0, nullable=False)
    requires_escalation: bool = Field(default=False, nullable=False)


class SessionProblemState(SQLModel, table=True):
    __tablename__ = "session_problem_state"

    session_id: UUID = Field(primary_key=True, foreign_key="conversation_session.id")
    category_id: Optional[UUID] = Field(default=None, foreign_key="problem_category.id")
    cause_id: Optional[UUID] = Field(default=None, foreign_key="problem_cause.id")
    classification_confidence: Optional[float] = Field(default=None, nullable=True)
    classification_source: Optional[str] = Field(default=None, sa_column=Column(String(length=64), nullable=True))
    manual_override: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class SessionSuggestion(SQLModel, table=True):
    __tablename__ = "session_suggestion"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    session_id: UUID = Field(foreign_key="conversation_session.id", nullable=False, index=True)
    solution_id: UUID = Field(foreign_key="problem_solution.id", nullable=False, index=True)
    status: SuggestionStatus = Field(
        default=SuggestionStatus.SUGGESTED,
        sa_column=Column(SAEnum(SuggestionStatus, name="suggestion_status_enum"), nullable=False),
    )
    notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    completed_at: Optional[datetime] = Field(default=None, nullable=True)


