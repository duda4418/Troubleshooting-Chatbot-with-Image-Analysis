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
from app.data.DTO.troubleshooting_dto import ProblemRequestType
from app.data.DTO.usage_dto import ModelUsageDetails
from app.data.repositories import (
    ConversationMessageRepository,
    ConversationSessionRepository,
    ModelUsageRepository,
)
from app.data.DTO.troubleshooting_dto import ProblemRequestType
from app.data.schemas.models import ConversationMessage, ConversationSession, MessageRole, ModelUsageLog
from app.services.conversation_context_service import ConversationContextService
from app.services.feedback_flow_service import FeedbackFlowService
from app.services.form_submission_service import FormProcessingResult, FormSubmissionService
from app.services.image_analysis_service import ImageAnalysisResult, ImageAnalysisService
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
    request_type: Optional[str] = None


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
        form_submission_service: FormSubmissionService,
        feedback_flow_service: FeedbackFlowService,
    ) -> None:
        self._session_repository = session_repository
        self._message_repository = message_repository
        self._image_analysis = image_analysis_service
        self._context_service = context_service
        self._classifier = classifier_service
        self._planner = planner_service
        self._response_service = response_service
        self._usage_repository = usage_repository
        self._form_submission = form_submission_service
        self._feedback_flow = feedback_flow_service

    async def handle_message(self, request: AssistantMessageRequest) -> AssistantMessageResponse:
        session = await self._get_or_create_session(request.session_id)
        if session.status != "in_progress":
            raise PermissionError("Conversation has already been completed.")

        session_id = session.id
        user_text = (request.text or "").strip()
        metadata = dict(request.metadata or {})
        if request.images_b64:
            metadata["image_count"] = len(request.images_b64)

        form_result = await self._form_submission.process(session_id, metadata)
        if form_result.metadata_updates:
            metadata.update(form_result.metadata_updates)

        user_message = await self._persist_user_message(
            session_id=session_id,
            content=user_text,
            metadata=metadata,
        )

        if request.images_b64:
            await self._maybe_analyze_images(session_id, user_message.id, request)

        context = await self._context_service.get_ai_context(session_id)

        decision = self._feedback_flow.handle_form_submission(form_result)
        if decision.handled:
            # Form was handled (escalation confirmed, resolution confirmed, or dismissed)
            if decision.answer:
                # We have a response to send
                assistant_message = await self._persist_assistant_message(
                    session_id=session_id,
                    answer=decision.answer,
                )
                if decision.completed_status:
                    await self._session_repository.set_status(session_id, decision.completed_status)
                else:
                    await self._session_repository.touch(session_id)
                return AssistantMessageResponse(
                    session_id=session_id,
                    user_message_id=user_message.id,
                    assistant_message_id=assistant_message.id,
                    answer=decision.answer,
                    knowledge_hits=[],
                    form_id=None,
                )
            else:
                # Form dismissed - no response needed, just update session
                await self._session_repository.touch(session_id)
                # Return response with empty answer (frontend should handle gracefully)
                return AssistantMessageResponse(
                    session_id=session_id,
                    user_message_id=user_message.id,
                    assistant_message_id=None,  # No assistant message created
                    answer=AssistantAnswer(reply="", suggested_actions=[], metadata={"dismissed": True}),
                    knowledge_hits=[],
                    form_id=None,
                )

        classification = await self._safe_classify(
            ProblemClassificationRequest(
                session_id=session_id,
                locale=request.locale,
                user_text=user_text,
                context=context,
            )
        )

        suggestion_plan: SuggestionPlan
        request_type = classification.request_type or ProblemRequestType.TROUBLESHOOT
        if request_type is ProblemRequestType.RESOLUTION_CHECK:
            classification.escalate = False
            classification.escalate_reason = None
            classification.needs_more_info = False
            classification.next_questions = []
            suggestion_plan = SuggestionPlan(
                solutions=[],
                escalate=False,
                notes="User reports the issue is resolved; confirm closure.",
            )
        elif request_type is ProblemRequestType.ESCALATION:
            classification.escalate = True
            classification.escalate_reason = classification.escalate_reason or "User requested human assistance."
            classification.needs_more_info = False
            classification.next_questions = []
            suggestion_plan = SuggestionPlan(
                solutions=[],
                escalate=True,
                notes=classification.escalate_reason,
            )
        elif request_type is ProblemRequestType.CLARIFICATION:
            classification.needs_more_info = True
            classification.escalate = False
            classification.escalate_reason = None
            suggestion_plan = SuggestionPlan(
                solutions=[],
                escalate=False,
                notes=classification.rationale or "Need clearer details before planning steps.",
            )
        else:
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
        self._attach_follow_up_forms(
            answer,
            classification,
            suggestion_plan,
            form_result,
        )

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

        if suggestion_plan.escalate and not answer.follow_up_form:
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
            request_type=classification.request_type.value if classification.request_type else None,
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
    ) -> Optional[ImageAnalysisResult]:
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
            return None
        if analysis_result.usage:
            await self._record_usage(
                session_id=session_id,
                message_id=message_id,
                usage=analysis_result.usage,
            )
        return analysis_result

    def _attach_follow_up_forms(
        self,
        answer: AssistantAnswer,
        classification: ProblemClassificationResult,
        plan: SuggestionPlan,
        form_result: FormProcessingResult,
    ) -> None:
        metadata: Dict[str, Any] = dict(answer.metadata or {})
        existing_form = answer.follow_up_form

        declared_type_raw = answer.follow_up_type or metadata.get("follow_up_type")
        normalized_type = (declared_type_raw or "").strip().lower()
        declared_type = normalized_type if normalized_type and normalized_type != "none" else None
        if normalized_type == "none":
            answer.follow_up_type = None
        declared_reason = answer.follow_up_reason or metadata.get("follow_up_reason")

        request_type_value = classification.request_type.value if classification.request_type else ""

        if not declared_type:
            if request_type_value == ProblemRequestType.ESCALATION.value or plan.escalate or classification.escalate:
                declared_type = "escalation"
                declared_reason = (
                    classification.escalate_reason
                    or plan.notes
                    or "Escalation recommended by planner."
                )
            elif request_type_value == ProblemRequestType.RESOLUTION_CHECK.value:
                declared_type = "resolution_check"
                declared_reason = declared_reason or plan.notes or classification.rationale or "Confirm the issue is fully resolved."
            elif plan.solutions and not classification.needs_more_info and not classification.next_questions:
                # Only attach feedback form when we're actually suggesting a solution to try
                # NOT when asking clarifying questions
                declared_type = "feedback"
                declared_reason = "Quick check-in after solution"
            else:
                return

        if declared_type == "escalation":
            if form_result.form_kind == "escalation" and form_result.escalation_confirmed is False:
                # Respect the user's latest decision.
                plan.escalate = False
                classification.escalate = False
                metadata.update(
                    {
                        "form_kind": "escalation",
                        "follow_up_type": "none",
                        "follow_up_reason": "User declined escalation",
                    }
                )
                answer.follow_up_type = None
                answer.follow_up_reason = None
                answer.metadata = metadata
                return

            if not existing_form or metadata.get("form_kind") != "escalation":
                answer.follow_up_form = self._feedback_flow.build_escalation_form()

            answer.follow_up_type = "escalation"
            answer.follow_up_reason = declared_reason
            metadata.update(
                {
                    "form_kind": "escalation",
                    "follow_up_type": "escalation",
                    "follow_up_reason": declared_reason,
                }
            )
            answer.metadata = metadata
            return

        if declared_type == "resolution_check":
            if not existing_form or metadata.get("form_kind") != "resolution_check":
                answer.follow_up_form = self._feedback_flow.build_resolution_form()

            reason = declared_reason or "Confirm the issue is fully resolved."
            answer.follow_up_type = "resolution_check"
            answer.follow_up_reason = reason
            metadata.update(
                {
                    "form_kind": "resolution_check",
                    "follow_up_type": "resolution_check",
                    "follow_up_reason": reason,
                }
            )
            answer.metadata = metadata
            return

        if declared_type == "feedback":
            if not existing_form or metadata.get("form_kind") != "feedback":
                answer.follow_up_form = self._feedback_flow.build_feedback_form()

            reason = declared_reason or "Quick check-in"
            answer.follow_up_type = "feedback"
            answer.follow_up_reason = reason
            metadata.update(
                {
                    "form_kind": "feedback",
                    "follow_up_type": "feedback",
                    "follow_up_reason": reason,
                }
            )
            answer.metadata = metadata
            return

        # If the service requested "none" or provided no follow-up, clear any stale values.
        metadata.pop("follow_up_type", None)
        if declared_type_raw and declared_type_raw.lower() not in {"", "none"}:
            metadata["follow_up_type"] = declared_type_raw
        if declared_reason:
            metadata["follow_up_reason"] = declared_reason
        else:
            metadata.pop("follow_up_reason", None)
        answer.follow_up_type = None
        answer.follow_up_reason = declared_reason
        answer.metadata = metadata

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
