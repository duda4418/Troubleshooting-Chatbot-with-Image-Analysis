from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.data.DTO.conversation_context_dto import ConversationAIContext
from app.data.DTO.knowledge_dto import KnowledgeHit


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
    question: str
    input_type: str
    required: bool = False
    placeholder: Optional[str] = None
    options: List[GeneratedFormOption] = Field(default_factory=list)


class GeneratedForm(BaseModel):
    title: str
    description: Optional[str] = None
    fields: List[GeneratedFormField] = Field(default_factory=list)


class ResponseGenerationRequest(BaseModel):
    session_id: UUID
    locale: str
    user_text: str
    context: ConversationAIContext
    knowledge_hits: List[KnowledgeHit] = Field(default_factory=list)
    recommendation_summary: Optional[str] = None


class AssistantAnswer(BaseModel):
    reply: str
    suggested_actions: List[str] = Field(default_factory=list)
    follow_up_form: Optional[GeneratedForm] = None
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageFlowResult(BaseModel):
    session_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID
    answer: AssistantAnswer
    knowledge_hits: List[KnowledgeHit] = Field(default_factory=list)
    form_id: Optional[UUID] = None
