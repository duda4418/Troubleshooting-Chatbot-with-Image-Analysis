from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.data.DTO.conversation_context_dto import ConversationAIContext


class UserMessageRequest(BaseModel):
    session_id: Optional[UUID] = None
    text: Optional[str] = None
    images_b64: List[str] = Field(default_factory=list)
    image_mime_types: Optional[List[Optional[str]]] = None
    locale: str = "en"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GeneratedFormOption(BaseModel):
    value: str
    label: str


class GeneratedFormField(BaseModel):
    field_id: Optional[str] = None  # Identifier for the field (e.g., "is_resolved")
    question: str
    input_type: str
    required: bool = False
    placeholder: Optional[str] = None
    options: List[GeneratedFormOption] = Field(default_factory=list)


class GeneratedForm(BaseModel):
    title: str
    description: Optional[str] = None
    fields: List[GeneratedFormField] = Field(default_factory=list)


class AssistantAnswer(BaseModel):
    reply: str
    suggested_actions: List[str] = Field(default_factory=list)
    follow_up_form: Optional[GeneratedForm] = None
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    follow_up_type: Optional[str] = None
    follow_up_reason: Optional[str] = None


