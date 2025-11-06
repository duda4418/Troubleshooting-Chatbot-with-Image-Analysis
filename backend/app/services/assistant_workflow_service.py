from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, Field  # type: ignore[import-untyped]

from app.data.DTO import (
    AssistantAnswer,
    AssistantMessageMetadata,
    AssistantMessageRequest,
    AssistantMessageResponse,
    ConversationMessageRead,
    ConversationSessionRead,
    ProblemClassificationRequest,
    ProblemClassificationResult,
    ResponseGenerationRequest,
    SuggestionPlan,
    SuggestionPlannerRequest,
)
from app.data.DTO.image_analysis_dto import ImageAnalysisRequest
from app.data.DTO.usage_dto import ModelUsageDetails
from app.data.repositories import (
    ConversationMessageRepository,
    ConversationSessionRepository,
    ModelUsageRepository,
)
from app.data.schemas.models import ConversationMessage, ConversationSession, MessageRole, ModelUsageLog
from app.services.conversation_context_service import ConversationContextService
from app.services.image_analysis_service import ImageAnalysisService
from app.services.problem_classifier_service import ProblemClassifierService
from app.services.response_generation_service import ResponseGenerationResult, ResponseGenerationService
from app.services.suggestion_planner_service import SuggestionPlannerService

logger = logging.getLogger(__name__)


class ClassificationEnvelope(BaseModel):
    confidence: Optional[float] = None
    rationale: Optional[str] = None
    escalate: bool = False
    escalate_reason: Optional[str] = None
    needs_more_info: bool = False
    category: Optional[Dict[str, str]] = None
    cause: Optional[Dict[str, str]] = None
    questions: List[str] = Field(default_factory=list)


class PlannedSolutionEnvelope(BaseModel):
    id: str
    slug: str
    title: str
    requires_escalation: bool
    already_suggested: bool


class PlanEnvelope(BaseModel):
    escalate: bool = False
    notes: Optional[str] = None
    solutions: List[PlannedSolutionEnvelope] = Field(default_factory=list)


class AssistantWorkflowService:
    """Deterministic workflow tying classifier, planner, and responder together."""

    def __init__(
        self,
        *,
        session_repository: ConversationSessionRepository,
        message_repository: ConversationMessageRepository,
        image_analysis_service: ImageAnalysisService,
        context_service: ConversationContextService,
        classifier_service: ProblemClassifierService,
        planner_service: SuggestionPlannerService,
        response_service: ResponseGenerationService,
        usage_repository: ModelUsageRepository,
    ) -> None:
        self._session_repository = session_repository
        self._message_repository = message_repository
        self._image_analysis = image_analysis_service
        self._context_service = context_service
        self._classifier = classifier_service
        self._planner = planner_service
        self._response_service = response_service
        self._usage_repository = usage_repository

    async def handle_message(self, request: AssistantMessageRequest) -> AssistantMessageResponse:
        session = await self._get_or_create_session(request.session_id)
        if session.status != "in_progress":
            raise PermissionError("Conversation has already been completed.")

        session_id = session.id
        user_text = (request.text or "").strip()
        metadata = dict(request.metadata or {})
        if request.images_b64:
            metadata["image_count"] = len(request.images_b64)

        user_message = await self._persist_user_message(
            session_id=session_id,
            content=user_text,
            metadata=metadata,
        )

        if request.images_b64:
            await self._maybe_analyze_images(session_id, user_message.id, request)

        context = await self._context_service.get_ai_context(session_id)

        classification = await self._safe_classify(
            ProblemClassificationRequest(
                session_id=session_id,
                locale=request.locale,
                user_text=user_text,
                context=context,
            )
        )

        suggestion_plan = await self._safe_plan(
            SuggestionPlannerRequest(
                session_id=session_id,
                classification=classification,
                max_suggestions=1,
            )
        )

        response_request = ResponseGenerationRequest(
            session_id=session_id,
            locale=request.locale,
            user_text=user_text,
            context=context,
            classification=classification,
            suggestion_plan=suggestion_plan,
        )
        generation_result: ResponseGenerationResult = await self._response_service.generate(response_request)
        answer = generation_result.answer

        self._embed_structured_metadata(answer, classification, suggestion_plan)

        assistant_message = await self._persist_assistant_message(
            session_id=session_id,
            answer=answer,
        )

        await self._planner.persist_new_suggestions(session_id, suggestion_plan)

        if generation_result.usage:
            await self._record_usage(
                session_id=session_id,
                message_id=assistant_message.id,
                usage=generation_result.usage,
            )

        if suggestion_plan.escalate:
            await self._session_repository.set_status(session_id, "escalated")
        else:
            await self._session_repository.touch(session_id)

        return AssistantMessageResponse(
            session_id=session_id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            answer=answer,
            knowledge_hits=[],
            form_id=None,
        )

    async def list_sessions(self, *, limit: int) -> List[ConversationSessionRead]:
        sessions = await self._session_repository.list_recent(limit=limit)
        return [ConversationSessionRead.model_validate(item, from_attributes=True) for item in sessions]

    async def get_session_history(
        self,
        session_id: UUID,
        limit: int,
    ) -> Tuple[ConversationSessionRead, List[ConversationMessageRead]]:
        session = await self._session_repository.get_by_id(session_id)
        if not session:
            raise ValueError("Session not found")
        messages = await self._message_repository.list_by_session(session_id=session_id, limit=limit)
        session_read = ConversationSessionRead.model_validate(session, from_attributes=True)
        message_reads = [ConversationMessageRead.model_validate(msg, from_attributes=True) for msg in messages]
        return session_read, message_reads

    async def submit_feedback(self, session_id: UUID, *, rating: int, comment: Optional[str] = None) -> None:
        session = await self._session_repository.get_by_id(session_id)
        if not session:
            raise ValueError("Session not found")
        if session.status == "in_progress":
            raise PermissionError("Conversation is still active.")
        await self._session_repository.set_feedback(session_id, rating=rating, comment=comment)

    async def _safe_classify(self, request: ProblemClassificationRequest) -> ProblemClassificationResult:
        try:
            return await self._classifier.classify(request)
        except Exception:  # noqa: BLE001
            logger.exception("Problem classification failed for session %s", request.session_id)
            return ProblemClassificationResult(
                rationale="Classification unavailable due to internal error.",
                needs_more_info=True,
            )

    async def _safe_plan(self, request: SuggestionPlannerRequest) -> SuggestionPlan:
        try:
            return await self._planner.plan(request)
        except Exception:  # noqa: BLE001
            logger.exception("Suggestion planning failed for session %s", request.session_id)
            return SuggestionPlan(notes="Planner encountered an internal error.")

    def _embed_structured_metadata(
        self,
        answer: AssistantAnswer,
        classification: ProblemClassificationResult,
        plan: SuggestionPlan,
    ) -> None:
        metadata: Dict[str, Any] = dict(answer.metadata or {})
        metadata["classification"] = self._build_classification_envelope(classification).model_dump(exclude_none=True)
        metadata["troubleshooting_plan"] = self._build_plan_envelope(plan).model_dump(exclude_none=True)
        answer.metadata = metadata

    @staticmethod
    def _build_classification_envelope(classification: ProblemClassificationResult) -> ClassificationEnvelope:
        payload = ClassificationEnvelope(
            confidence=classification.confidence,
            rationale=classification.rationale,
            escalate=classification.escalate,
            escalate_reason=classification.escalate_reason,
            needs_more_info=classification.needs_more_info,
        )
        if classification.category:
            payload.category = {
                "id": str(classification.category.id),
                "slug": classification.category.slug,
                "name": classification.category.name,
            }
        if classification.cause:
            payload.cause = {
                "id": str(classification.cause.id),
                "slug": classification.cause.slug,
                "name": classification.cause.name,
            }
        if classification.next_questions:
            payload.questions = [q for q in classification.next_questions if q]
        return payload

    @staticmethod
    def _build_plan_envelope(plan: SuggestionPlan) -> PlanEnvelope:
        solutions = [
            PlannedSolutionEnvelope(
                id=str(item.solution.id),
                slug=item.solution.slug,
                title=item.solution.title,
                requires_escalation=item.solution.requires_escalation,
                already_suggested=item.already_suggested,
            )
            for item in plan.solutions
        ]
        return PlanEnvelope(
            escalate=plan.escalate,
            notes=plan.notes,
            solutions=solutions,
        )

    async def _get_or_create_session(self, session_id: Optional[UUID]) -> ConversationSession:
        if session_id:
            existing = await self._session_repository.get_by_id(session_id)
            if existing:
                return existing
            logger.warning("Session %s not found, creating a new one", session_id)
        session = ConversationSession(id=uuid4())
        return await self._session_repository.create(session)

    async def _persist_user_message(
        self,
        *,
        session_id: UUID,
        content: str,
        metadata: Dict[str, Any],
    ) -> ConversationMessage:
        message = ConversationMessage(
            session_id=session_id,
            role=MessageRole.USER,
            content=content,
            message_metadata=dict(metadata),
        )
        return await self._message_repository.create(message)

    async def _persist_assistant_message(
        self,
        *,
        session_id: UUID,
        answer: AssistantAnswer,
    ) -> ConversationMessage:
        metadata_model = AssistantMessageMetadata.from_answer(answer, knowledge_hits=[])
        message = ConversationMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=answer.reply,
            message_metadata=metadata_model.to_message_metadata(),
        )
        return await self._message_repository.create(message)

    async def _maybe_analyze_images(
        self,
        session_id: UUID,
        message_id: UUID,
        request: AssistantMessageRequest,
    ) -> None:
        analysis_request = ImageAnalysisRequest(
            session_id=session_id,
            message_id=message_id,
            images_b64=request.images_b64,
            image_mime_types=request.image_mime_types,
            locale=request.locale,
            user_prompt=request.text,
        )
        try:
            analysis_result = await self._image_analysis.analyze_and_store(analysis_request)
        except Exception:  # noqa: BLE001
            logger.exception("Image analysis failed for session %s", session_id)
            return
        if analysis_result.usage:
            await self._record_usage(
                session_id=session_id,
                message_id=message_id,
                usage=analysis_result.usage,
            )

    async def _record_usage(
        self,
        *,
        session_id: UUID,
        message_id: UUID,
        usage: ModelUsageDetails,
    ) -> None:
        record = ModelUsageLog(
            session_id=session_id,
            message_id=message_id,
            request_type=usage.request_type,
            model=usage.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            cost_input=usage.cost_input,
            cost_output=usage.cost_output,
            cost_total=usage.cost_total,
            usage_metadata=usage.raw_usage,
        )
        try:
            await self._usage_repository.create(record)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to persist model usage for session %s", session_id)
