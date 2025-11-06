from functools import lru_cache

from app.core.config import settings
from app.core.database import DatabaseProvider, get_db_provider
from app.data.repositories import (
    ConversationMessageRepository,
    ConversationSessionRepository,
    ConversationImageRepository,
    ModelUsageRepository,
)
from app.services import (
    AssistantService,
    ChromaService,
    ConversationContextService,
    FeedbackFlowService,
    FormSubmissionService,
    ImageAnalysisService,
    MetricsService,
    RecommendationTracker,
    ResponseGenerationService,
)
from app.tools import KnowledgeSearchTool, MachineConfigTool, TicketTool


@lru_cache()
def get_database_provider() -> DatabaseProvider:
    return get_db_provider()


@lru_cache()
def get_conversation_session_repository() -> ConversationSessionRepository:
    return ConversationSessionRepository(get_database_provider())


@lru_cache()
def get_conversation_message_repository() -> ConversationMessageRepository:
    return ConversationMessageRepository(get_database_provider())


@lru_cache()
def get_conversation_image_repository() -> ConversationImageRepository:
    return ConversationImageRepository(get_database_provider())


@lru_cache()
def get_model_usage_repository() -> ModelUsageRepository:
    return ModelUsageRepository(get_database_provider())

@lru_cache()
def get_chroma_service() -> ChromaService:
    return ChromaService()


@lru_cache()
def get_knowledge_search_tool() -> KnowledgeSearchTool:
    return KnowledgeSearchTool(get_chroma_service())


@lru_cache()
def get_machine_config_tool() -> MachineConfigTool:
    return MachineConfigTool()


@lru_cache()
def get_ticket_tool() -> TicketTool:
    return TicketTool()


@lru_cache()
def get_conversation_context_service() -> ConversationContextService:
    return ConversationContextService(
        get_conversation_session_repository(),
        get_conversation_image_repository(),
    )


@lru_cache()
def get_form_submission_service() -> FormSubmissionService:
    return FormSubmissionService(get_conversation_message_repository())


@lru_cache()
def get_recommendation_tracker() -> RecommendationTracker:
    return RecommendationTracker(get_conversation_message_repository())


@lru_cache()
def get_image_analysis_service() -> ImageAnalysisService:
    return ImageAnalysisService(
        get_conversation_image_repository(),
        api_key=settings.OPENAI_API_KEY,
        vision_model=settings.OPENAI_VISION_MODEL,
    )


@lru_cache()
def get_response_generation_service() -> ResponseGenerationService:
    return ResponseGenerationService(
        api_key=settings.OPENAI_API_KEY,
        response_model=settings.OPENAI_RESPONSE_MODEL,
    )


@lru_cache()
def get_feedback_flow_service() -> FeedbackFlowService:
    return FeedbackFlowService()


@lru_cache()
def get_assistant_service() -> AssistantService:
    return AssistantService(
        session_repository=get_conversation_session_repository(),
        message_repository=get_conversation_message_repository(),
        image_analysis_service=get_image_analysis_service(),
        context_service=get_conversation_context_service(),
        form_submission_service=get_form_submission_service(),
        feedback_flow_service=get_feedback_flow_service(),
        recommendation_tracker=get_recommendation_tracker(),
        response_service=get_response_generation_service(),
        usage_repository=get_model_usage_repository(),
        knowledge_tool=get_knowledge_search_tool(),
        ticket_tool=get_ticket_tool(),
    )


@lru_cache()
def get_metrics_service() -> MetricsService:
    return MetricsService(
        session_repository=get_conversation_session_repository(),
        message_repository=get_conversation_message_repository(),
        usage_repository=get_model_usage_repository(),
    )
