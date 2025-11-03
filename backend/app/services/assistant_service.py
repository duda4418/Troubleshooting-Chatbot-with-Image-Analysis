from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from app.data.DTO import (
    AssistantMessageRequest,
    AssistantMessageResponse,
    AssistantAnswer,
    ConversationMessageRead,
    ConversationSessionRead,
    GeneratedForm,
    GeneratedFormField,
    GeneratedFormOption,
    KnowledgeHit,
    ResponseGenerationRequest,
)
from app.data.DTO.image_analysis_dto import ImageAnalysisRequest
from app.data.repositories import (
    ConversationMessageRepository,
    ConversationSessionRepository,
)
from app.data.schemas.models import ConversationMessage, ConversationSession, MessageRole
from app.services.conversation_context_service import ConversationContextService
from app.services.image_analysis_service import ImageAnalysisService
from app.services.form_submission_service import FormSubmissionService
from app.services.feedback_flow_service import FeedbackFlowService
from app.services.recommendation_tracker import RecommendationTracker
from app.services.response_generation_service import ResponseGenerationService
from app.tools.knowledge_tool import KnowledgeSearchTool
from app.tools.ticket_tool import TicketTool

logger = logging.getLogger(__name__)


class AssistantService:
    """High-level orchestrator for assistant conversations."""

    def __init__(
        self,
        *,
        session_repository: ConversationSessionRepository,
        message_repository: ConversationMessageRepository,
        image_analysis_service: ImageAnalysisService,
        context_service: ConversationContextService,
        form_submission_service: FormSubmissionService,
        feedback_flow_service: FeedbackFlowService,
        recommendation_tracker: RecommendationTracker,
        response_service: ResponseGenerationService,
        knowledge_tool: Optional[KnowledgeSearchTool] = None,
        ticket_tool: Optional[TicketTool] = None,
    ) -> None:
        self._session_repository = session_repository
        self._message_repository = message_repository
        self._image_analysis = image_analysis_service
        self._context_service = context_service
        self._form_submission_service = form_submission_service
        self._feedback_flow = feedback_flow_service
        self._recommendation_tracker = recommendation_tracker
        self._response_service = response_service
        self._knowledge_tool = knowledge_tool
        self._ticket_tool = ticket_tool
        self._random = random.Random()
        self._feedback_form_probability = 0.25

    async def handle_message(self, request: AssistantMessageRequest) -> AssistantMessageResponse:
        session = await self._get_or_create_session(request.session_id)
        session_id = session.id

        if session.status != "in_progress":
            raise PermissionError("Conversation has already been completed.")

        metadata = dict(request.metadata or {})
        history = await self._recommendation_tracker.build_history(session_id)

        form_result = await self._form_submission_service.process(session_id, metadata)
        metadata = self._merge_metadata(metadata, form_result.metadata_updates)

        completed_status: Optional[str] = None
        if form_result.resolved:
            completed_status = "resolved"

        form_summary = form_result.summary
        ticket_details: Optional[Dict[str, Any]] = None
        if form_result.escalation_confirmed and self._ticket_tool and not self._metadata_has_ticket(metadata):
            ticket_details = await self._open_ticket(
                session_id=session_id,
                summary=self._build_ticket_summary(request.text, form_summary),
            )
            if ticket_details:
                ticket_line = self._format_ticket_line(ticket_details)
                form_summary = f"{form_summary}\n\n{ticket_line}" if form_summary else ticket_line
                metadata = self._merge_metadata(
                    metadata,
                    {
                        "ticket": ticket_details,
                        "follow_up_form_summary": form_summary,
                        "extra": {"ticket": ticket_details},
                    },
                )
                completed_status = "escalated"

        combined_user_text = self._compose_user_text(request.text, form_summary)

        if request.images_b64:
            metadata["image_count"] = len(request.images_b64)

        user_message = await self._persist_user_message(
            session_id,
            content=combined_user_text,
            metadata=metadata,
        )

        if request.images_b64:
            await self._maybe_analyze_images(session_id, user_message.id, request)

        follow_up_decision = self._feedback_flow.handle_form_submission(form_result)
        if follow_up_decision.completed_status:
            completed_status = follow_up_decision.completed_status

        knowledge_hits: List[KnowledgeHit] = []
        if form_result.skip_response:
            answer = AssistantAnswer(
                reply="",
                suggested_actions=[],
                follow_up_form=None,
                confidence=None,
                metadata={"client_hidden": True},
            )
        elif follow_up_decision.handled:
            answer = follow_up_decision.answer or AssistantAnswer(
                reply="",
                suggested_actions=[],
                follow_up_form=None,
                confidence=None,
                metadata={},
            )
        else:
            knowledge_hits = await self._maybe_lookup_knowledge(combined_user_text)
            recent_assistant_messages = await self._message_repository.list_recent_by_role(
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                limit=5,
            )

            context = await self._context_service.get_ai_context(session_id)
            response_request = ResponseGenerationRequest(
                session_id=session_id,
                locale=request.locale,
                user_text=combined_user_text,
                context=context,
                knowledge_hits=knowledge_hits,
                recommendation_summary=history.context_summary(),
            )
            answer = await self._response_service.generate(response_request)

            self._apply_follow_up_directive(
                answer,
                prior_messages=recent_assistant_messages,
            )

            self._maybe_offer_quick_check(
                answer,
                prior_messages=recent_assistant_messages,
            )

            if ticket_details:
                self._attach_ticket_metadata(answer, ticket_details)

        assistant_message = await self._persist_assistant_message(
            session_id=session_id,
            answer=answer,
            knowledge_hits=knowledge_hits,
        )

        if completed_status:
            await self._session_repository.close(session_id, status=completed_status)
        else:
            await self._session_repository.touch(session_id)

        return AssistantMessageResponse(
            session_id=session_id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            answer=answer,
            knowledge_hits=knowledge_hits,
            form_id=None,
        )

    async def list_sessions(self, *, limit: int) -> List[ConversationSessionRead]:
        sessions = await self._session_repository.list_recent(limit=limit)
        return [
            ConversationSessionRead.model_validate(session, from_attributes=True)
            for session in sessions
        ]

    async def get_session_history(
        self, session_id: UUID, limit: int
    ) -> Tuple[ConversationSessionRead, List[ConversationMessageRead]]:
        session = await self._session_repository.get_by_id(session_id)
        if not session:
            raise ValueError("Session not found")

        messages = await self._message_repository.list_by_session(session_id=session_id, limit=limit)
        session_read = ConversationSessionRead.model_validate(session, from_attributes=True)
        message_reads = [
            ConversationMessageRead.model_validate(message, from_attributes=True)
            for message in messages
        ]
        return session_read, message_reads

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
        session_id: UUID,
        *,
        content: str,
        metadata: Dict[str, Any],
    ) -> ConversationMessage:
        metadata_copy = dict(metadata)
        message = ConversationMessage(
            session_id=session_id,
            role=MessageRole.USER,
            content=content,
            message_metadata=metadata_copy,
        )
        return await self._message_repository.create(message)

    async def submit_feedback(self, session_id: UUID, *, rating: int, comment: Optional[str] = None) -> None:
        session = await self._session_repository.get_by_id(session_id)
        if not session:
            raise ValueError("Session not found")
        if session.status == "in_progress":
            raise PermissionError("Conversation is still active.")
        await self._session_repository.set_feedback(session_id, rating=rating, comment=comment)

    async def _persist_assistant_message(
        self,
        *,
        session_id: UUID,
        answer: AssistantAnswer,
        knowledge_hits: List[KnowledgeHit],
    ) -> ConversationMessage:
        extra_metadata = dict(answer.metadata or {})
        metadata = {
            "suggested_actions": answer.suggested_actions,
            "follow_up_form": answer.follow_up_form.model_dump() if answer.follow_up_form else None,
            "confidence": answer.confidence,
            "knowledge_hits": [hit.model_dump() for hit in knowledge_hits],
        }
        client_hidden = extra_metadata.pop("client_hidden", None)
        if isinstance(client_hidden, bool):
            metadata["client_hidden"] = client_hidden

        follow_up_type = extra_metadata.pop("follow_up_type", None)
        if isinstance(follow_up_type, str) and follow_up_type.strip():
            metadata["follow_up_type"] = follow_up_type.strip()

        follow_up_reason = extra_metadata.pop("follow_up_reason", None)
        if isinstance(follow_up_reason, str) and follow_up_reason.strip():
            metadata["follow_up_reason"] = follow_up_reason.strip()

        form_kind_extra = extra_metadata.get("form_kind")
        if isinstance(form_kind_extra, str):
            metadata["form_kind"] = form_kind_extra

        summary_extra = extra_metadata.get("follow_up_form_summary")
        if isinstance(summary_extra, str):
            metadata["follow_up_form_summary"] = summary_extra

        if extra_metadata:
            metadata["extra"] = extra_metadata

        message = ConversationMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=answer.reply,
            message_metadata=metadata,
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
            await self._image_analysis.analyze_and_store(analysis_request)
        except Exception:  # noqa: BLE001
            logger.exception("Image analysis failed for session %s", session_id)

    async def _maybe_lookup_knowledge(self, query: Optional[str]) -> List[KnowledgeHit]:
        text = (query or "").strip()
        if not text or not self._knowledge_tool:
            return []
        try:
            result = await self._knowledge_tool.run(query=text)
        except Exception:  # noqa: BLE001
            logger.exception("Knowledge search failed")
            return []

        if not result.success:
            return []

        hits: List[KnowledgeHit] = []
        for item in result.details.get("hits", []) or []:
            try:
                hits.append(KnowledgeHit.model_validate(item))
            except Exception:  # noqa: BLE001
                logger.debug("Skipping malformed knowledge hit: %s", item)
        return hits

    def _apply_follow_up_directive(
        self,
        answer: AssistantAnswer,
        *,
        prior_messages: List[ConversationMessage],
    ) -> None:
        follow_up_type = (answer.follow_up_type or "").strip().lower()
        metadata = dict(answer.metadata or {})

        if not follow_up_type or follow_up_type == "none":
            metadata.pop("follow_up_type", None)
            answer.follow_up_type = None
            if answer.follow_up_reason:
                metadata["follow_up_reason"] = answer.follow_up_reason
            answer.follow_up_form = None
            answer.metadata = metadata
            return

        metadata["follow_up_type"] = follow_up_type
        if answer.follow_up_reason:
            metadata["follow_up_reason"] = answer.follow_up_reason

        if follow_up_type == "escalation":
            if self._recent_form_kind(prior_messages, "escalation", limit=1):
                # Avoid spamming escalation prompts
                metadata.pop("follow_up_type", None)
                metadata.pop("follow_up_reason", None)
                answer.follow_up_form = None
                answer.follow_up_type = None
            else:
                metadata.setdefault("escalation", {"status": "recommended"})
                metadata["form_kind"] = "escalation"
                if answer.follow_up_form is None:
                    answer.follow_up_form = self._build_escalation_form()
        elif follow_up_type == "resolution_check":
            if self._recent_form_kind(prior_messages, "resolution_check", limit=1):
                metadata.pop("follow_up_type", None)
                metadata.pop("follow_up_reason", None)
                answer.follow_up_form = None
                answer.follow_up_type = None
            else:
                metadata["form_kind"] = "resolution_check"
                if answer.follow_up_form is None:
                    answer.follow_up_form = FeedbackFlowService.build_resolution_form()
        else:
            metadata.setdefault("form_kind", follow_up_type)

        answer.metadata = metadata

    def _maybe_offer_quick_check(
        self,
        answer: AssistantAnswer,
        *,
        prior_messages: List[ConversationMessage],
    ) -> None:
        if answer.follow_up_form is not None:
            return
        if (answer.follow_up_type or "").strip():
            return
        if not answer.suggested_actions:
            return
        if self._recent_form_kind(prior_messages, "feedback", limit=3):
            return
        if self._random.random() > self._feedback_form_probability:
            return

        metadata = dict(answer.metadata or {})
        metadata["form_kind"] = "feedback"
        metadata["follow_up_type"] = "feedback"
        metadata.setdefault(
            "follow_up_reason",
            "Quick check after new troubleshooting steps",
        )

        answer.follow_up_form = FeedbackFlowService.build_feedback_form()
        answer.follow_up_type = "feedback"
        answer.follow_up_reason = metadata["follow_up_reason"]
        answer.metadata = metadata

    @staticmethod
    def _recent_form_kind(
        messages: List[ConversationMessage],
        kind: str,
        *,
        limit: int,
    ) -> bool:
        target = kind.lower()
        for index, message in enumerate(messages):
            if index >= limit:
                break
            metadata = message.message_metadata or {}
            if not isinstance(metadata, dict):
                continue
            value = metadata.get("form_kind")
            if isinstance(value, str) and value.strip().lower() == target:
                return True
            extra = metadata.get("extra")
            if isinstance(extra, dict):
                nested = extra.get("form_kind")
                if isinstance(nested, str) and nested.strip().lower() == target:
                    return True
        return False

    @staticmethod
    def _compose_user_text(
        original_text: Optional[str],
        form_summary: Optional[str],
    ) -> str:
        parts: List[str] = []
        if original_text and original_text.strip():
            parts.append(original_text.strip())
        if form_summary:
            parts.append(form_summary)
        return "\n\n".join(parts)

    @staticmethod
    def _build_escalation_form() -> GeneratedForm:
        return GeneratedForm(
            title="Escalate?",
            description="Should I connect you with a technician?",
            fields=[
                GeneratedFormField(
                    question="Would you like to escalate this to a technician?",
                    input_type="single_choice",
                    required=True,
                    options=[
                        GeneratedFormOption(value="yes", label="Yes, escalate it"),
                        GeneratedFormOption(value="no", label="No, keep troubleshooting"),
                    ],
                )
            ],
        )

    @staticmethod
    def _merge_metadata(original: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        if not updates:
            return original
        merged = dict(original)
        for key, value in updates.items():
            if key == "extra":
                existing_extra = merged.get("extra")
                if isinstance(existing_extra, dict) and isinstance(value, dict):
                    combined = dict(existing_extra)
                    combined.update(value)
                    merged["extra"] = combined
                    continue
            merged[key] = value
        return merged

    @staticmethod
    def _metadata_has_ticket(metadata: Dict[str, Any]) -> bool:
        if isinstance(metadata.get("ticket"), dict):
            return True
        extra = metadata.get("extra")
        if isinstance(extra, dict) and isinstance(extra.get("ticket"), dict):
            return True
        return False

    async def _open_ticket(self, session_id: UUID, *, summary: str) -> Optional[Dict[str, Any]]:
        if not self._ticket_tool:
            return None
        try:
            result = await self._ticket_tool.run(consent=True, summary=summary, session_id=str(session_id))
        except Exception:  # noqa: BLE001
            logger.exception("Ticket tool failed for session %s", session_id)
            return None
        if not result.success:
            logger.warning("Ticket tool unsuccessful for session %s: %s", session_id, result.details)
            return None
        return result.details

    @staticmethod
    def _build_ticket_summary(user_text: Optional[str], form_summary: Optional[str]) -> str:
        parts: List[str] = []
        if form_summary:
            parts.append(form_summary)
        if user_text and user_text.strip():
            parts.append(f"User note: {user_text.strip()}")
        if not parts:
            return "Escalation approved via follow-up form."
        return "\n\n".join(parts)

    @staticmethod
    def _format_ticket_line(ticket_details: Dict[str, Any]) -> str:
        ticket_id = ticket_details.get("ticket_id") or "TICKET"
        created_at = ticket_details.get("created_at")
        if isinstance(created_at, str) and created_at.strip():
            return f"Ticket created: {ticket_id} (opened at {created_at})."
        return f"Ticket created: {ticket_id}."

    def _attach_ticket_metadata(self, answer: AssistantAnswer, ticket_details: Dict[str, Any]) -> None:
        metadata = dict(answer.metadata or {})
        escalation = metadata.get("escalation")
        if isinstance(escalation, dict):
            combined = dict(escalation)
        else:
            combined = {}
        combined.setdefault("status", "ticket_opened")
        metadata["escalation"] = combined
        metadata.setdefault("form_kind", "escalation")
        metadata.setdefault("ticket", ticket_details)
        answer.metadata = metadata

        ticket_id = ticket_details.get("ticket_id")
        if isinstance(ticket_id, str) and ticket_id and ticket_id not in answer.reply:
            confirmation = (
                f"I've opened ticket {ticket_id} for our technicians. They'll follow up with next steps shortly."
            )
            answer.reply = self._append_with_spacing(answer.reply, confirmation)

    @staticmethod
    def _append_with_spacing(original: str, addition: str) -> str:
        base = (original or "").rstrip()
        if not base:
            return addition
        return f"{base}\n\n{addition}"
