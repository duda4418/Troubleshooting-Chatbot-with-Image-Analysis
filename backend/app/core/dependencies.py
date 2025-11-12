from functools import lru_cache

from app.core.config import settings
from app.core.database import DatabaseProvider, get_db_provider
from app.data.repositories import (
    ConversationImageRepository,
    ConversationMessageRepository,
    ConversationSessionRepository,
    ModelUsageRepository,
    ProblemCategoryRepository,
    ProblemCauseRepository,
    ProblemSolutionRepository,
    SessionProblemStateRepository,
    SessionSuggestionRepository,
)
from app.services import (
    ConversationContextService,
    ImageAnalysisService,
    MetricsService,
    TroubleshootingImportService,
)
from app.services_v2 import (
    UnifiedClassifierService,
    UnifiedResponseService,
    UnifiedWorkflowService,
    FormBuilderService,
    SessionManagerService,
)
from app.tools import MachineConfigTool


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
def get_problem_category_repository() -> ProblemCategoryRepository:
    return ProblemCategoryRepository(get_database_provider())


@lru_cache()
def get_problem_cause_repository() -> ProblemCauseRepository:
    return ProblemCauseRepository(get_database_provider())


@lru_cache()
def get_problem_solution_repository() -> ProblemSolutionRepository:
    return ProblemSolutionRepository(get_database_provider())


@lru_cache()
def get_session_problem_state_repository() -> SessionProblemStateRepository:
    return SessionProblemStateRepository(get_database_provider())


@lru_cache()
def get_session_suggestion_repository() -> SessionSuggestionRepository:
    return SessionSuggestionRepository(get_database_provider())

@lru_cache()
def get_machine_config_tool() -> MachineConfigTool:
    return MachineConfigTool()

@lru_cache()
def get_conversation_context_service() -> ConversationContextService:
    return ConversationContextService(
        get_conversation_session_repository(),
        get_conversation_image_repository(),
    )

@lru_cache()
def get_image_analysis_service() -> ImageAnalysisService:
    return ImageAnalysisService(
        get_conversation_image_repository(),
        api_key=settings.OPENAI_API_KEY,
        vision_model=settings.OPENAI_VISION_MODEL,
    )


@lru_cache()
def get_unified_classifier_service() -> UnifiedClassifierService:
    return UnifiedClassifierService(
        category_repository=get_problem_category_repository(),
        cause_repository=get_problem_cause_repository(),
        solution_repository=get_problem_solution_repository(),
        suggestion_repository=get_session_suggestion_repository(),
        problem_state_repository=get_session_problem_state_repository(),
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_RESPONSE_MODEL,
    )


@lru_cache()
def get_unified_response_service() -> UnifiedResponseService:
    return UnifiedResponseService(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_RESPONSE_MODEL,
    )


@lru_cache()
def get_form_builder_service() -> FormBuilderService:
    return FormBuilderService()


@lru_cache()
def get_session_manager_service() -> SessionManagerService:
    return SessionManagerService(
        session_repo=get_conversation_session_repository(),
        message_repo=get_conversation_message_repository(),
    )


@lru_cache()
def get_assistant_service() -> UnifiedWorkflowService:
    return UnifiedWorkflowService(
        classifier=get_unified_classifier_service(),
        response_generator=get_unified_response_service(),
        form_builder=get_form_builder_service(),
        context_service=get_conversation_context_service(),
        image_analysis=get_image_analysis_service(),
        session_repo=get_conversation_session_repository(),
        message_repo=get_conversation_message_repository(),
        suggestion_repo=get_session_suggestion_repository(),
        solution_repo=get_problem_solution_repository(),
        usage_repo=get_model_usage_repository(),
    )


@lru_cache()
def get_troubleshooting_import_service() -> TroubleshootingImportService:
    return TroubleshootingImportService(
        category_repository=get_problem_category_repository(),
        cause_repository=get_problem_cause_repository(),
        solution_repository=get_problem_solution_repository(),
    )


@lru_cache()
def get_metrics_service() -> MetricsService:
    return MetricsService(
        session_repository=get_conversation_session_repository(),
        message_repository=get_conversation_message_repository(),
        usage_repository=get_model_usage_repository(),
    )
