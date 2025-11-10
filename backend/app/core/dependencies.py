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
    AssistantWorkflowService,
    ConversationContextService,
    FeedbackFlowService,
    ImageAnalysisService,
    FormSubmissionService,
    MetricsService,
    ProblemClassifierService,
    ResponseGenerationService,
    SuggestionPlannerService,
    TroubleshootingImportService,
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
def get_response_generation_service() -> ResponseGenerationService:
    return ResponseGenerationService(
        api_key=settings.OPENAI_API_KEY,
        response_model=settings.OPENAI_RESPONSE_MODEL,
    )


@lru_cache()
def get_problem_classifier_service() -> ProblemClassifierService:
    return ProblemClassifierService(
        category_repository=get_problem_category_repository(),
        cause_repository=get_problem_cause_repository(),
        session_state_repository=get_session_problem_state_repository(),
        api_key=settings.OPENAI_API_KEY,
        response_model=settings.OPENAI_RESPONSE_MODEL,
    )


@lru_cache()
def get_suggestion_planner_service() -> SuggestionPlannerService:
    return SuggestionPlannerService(
        solution_repository=get_problem_solution_repository(),
        session_suggestion_repository=get_session_suggestion_repository(),
    )


@lru_cache()
def get_form_submission_service() -> FormSubmissionService:
    return FormSubmissionService(get_conversation_message_repository())


@lru_cache()
def get_feedback_flow_service() -> FeedbackFlowService:
    return FeedbackFlowService()


@lru_cache()
def get_assistant_service() -> AssistantWorkflowService:
    return AssistantWorkflowService(
        session_repository=get_conversation_session_repository(),
        message_repository=get_conversation_message_repository(),
        image_analysis_service=get_image_analysis_service(),
        context_service=get_conversation_context_service(),
        classifier_service=get_problem_classifier_service(),
        planner_service=get_suggestion_planner_service(),
        response_service=get_response_generation_service(),
        usage_repository=get_model_usage_repository(),
        form_submission_service=get_form_submission_service(),
        feedback_flow_service=get_feedback_flow_service(),
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
