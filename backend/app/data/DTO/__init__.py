"""
Data Transfer Objects (DTOs) for API request and response handling.

This module contains Pydantic models for:
- Request DTOs: Data coming into the API
- Response DTOs: Data sent back from the API
- Internal DTOs: Data transfer between layers

These DTOs provide:
- Input validation
- Type safety
- Clear API contracts
- Separation of concerns between API models and database models
"""

from .assistant_api_dto import (
    AssistantMessageRequest,
    AssistantMessageResponse,
    ConversationHistoryResponse,
    ConversationMessageRead,
    ConversationSessionRead,
)
from .conversation_context_dto import (
    ConversationAIContext,
)
from .image_analysis_dto import (
    ImageAnalysisRequest,
    ImageAnalysisResponse,
    ImageAnalysisSummary,
)
from .knowledge_dto import (
    AssistantToolResult,
    KnowledgeHit,
)
from .message_flow_dto import (
    AssistantAnswer,
    GeneratedForm,
    GeneratedFormField,
    GeneratedFormOption,
    MessageFlowResult,
    ResponseGenerationRequest,
    UserMessageRequest,
)

__all__ = [
    "AssistantMessageRequest",
    "AssistantMessageResponse",
    "ConversationHistoryResponse",
    "ConversationMessageRead",
    "ConversationSessionRead",
    "ConversationAIContext",
    "ImageAnalysisRequest",
    "ImageAnalysisResponse",
    "ImageAnalysisSummary",
    "AssistantToolResult",
    "KnowledgeHit",
    "AssistantAnswer",
    "GeneratedForm",
    "GeneratedFormField",
    "GeneratedFormOption",
    "MessageFlowResult",
    "ResponseGenerationRequest",
    "UserMessageRequest",
]