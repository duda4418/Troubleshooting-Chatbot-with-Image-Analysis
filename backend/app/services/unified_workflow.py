"""Unified workflow service - simplified orchestration of the new architecture.

This service:
1. Calls classifier (makes all decisions)
2. Calls response generator (creates friendly text)
3. Attaches forms based on classification decisions
4. Persists messages and tracks usage

Much simpler than the old workflow - no complex branching logic.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from app.data.DTO.conversation_context_dto import ConversationAIContext
from app.data.DTO.message_flow_dto import AssistantAnswer, GeneratedForm, UserMessageRequest
from app.data.DTO.simplified_flow_dto import ClassificationRequest, NextAction, ResponseRequest
from app.data.repositories import (
    ConversationMessageRepository,
    ConversationSessionRepository,
    ModelUsageRepository,
    ProblemSolutionRepository,
)
from app.data.repositories.session_suggestion_repository import SessionSuggestionRepository
from app.data.schemas.models import ConversationMessage, ConversationSession, MessageRole, ModelUsageLog
from app.services.conversation_context_service import ConversationContextService
from app.services.image_analysis_service import ImageAnalysisService
from app.services.utils.image_payload import resolve_image_mime
from app.services.unified_classifier import UnifiedClassifierService
from app.services.unified_response import UnifiedResponseService
from app.services.form_builder_service import FormBuilderService

logger = logging.getLogger(__name__)


class UnifiedWorkflowService:
    """Simplified workflow orchestration."""
    
    def __init__(
        self,
        *,
        classifier: UnifiedClassifierService,
        response_generator: UnifiedResponseService,
        form_builder: FormBuilderService,
        context_service: ConversationContextService,
        image_analysis: ImageAnalysisService,
        session_repo: ConversationSessionRepository,
        message_repo: ConversationMessageRepository,
        suggestion_repo: SessionSuggestionRepository,
        solution_repo: ProblemSolutionRepository,
        usage_repo: ModelUsageRepository,
    ):
        self._classifier = classifier
        self._response_generator = response_generator
        self._form_builder = form_builder
        self._context_service = context_service
        self._image_analysis = image_analysis
        self._session_repo = session_repo
        self._message_repo = message_repo
        self._suggestion_repo = suggestion_repo
        self._solution_repo = solution_repo
        self._usage_repo = usage_repo
    
    async def handle_message(self, request: UserMessageRequest):
        """Main entry point - handle user message."""
        
        logger.info("=" * 80)
        logger.info("NEW MESSAGE WORKFLOW STARTED")
        logger.info("=" * 80)
        
        # Get or create session
        session = await self._get_or_create_session(request.session_id)
        session_id = session.id
        
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Session Status: {session.status}")
        
        if session.status in ("resolved", "escalated"):
            raise PermissionError("Conversation already completed")
        
        # Check if this is a form dismissal (not submission)
        form_response = request.metadata.get("follow_up_form_response", {})
        is_form_interaction = request.metadata.get("client_hidden", False) and isinstance(form_response, dict)
        is_dismissal = is_form_interaction and form_response.get("status") == "dismissed"
        
        # Mark the original form as consumed if this is a form interaction
        if is_form_interaction:
            replied_to_id = form_response.get("replied_to")
            if replied_to_id:
                await self._mark_form_consumed(replied_to_id)
        
        if is_dismissal:
            logger.info("Form dismissal detected - skipping AI processing")
            # Just persist the user message with dismissal metadata and return
            user_message = await self._persist_user_message(
                session_id=session_id,
                content=request.text or "",
                request=request,
            )
            logger.info(f"Dismissal message persisted: {user_message.id}")
            logger.info("=" * 80)
            
            from app.data.DTO.assistant_api_dto import AssistantMessageResponse
            
            # Return without creating an assistant message
            return AssistantMessageResponse(
                session_id=session_id,
                user_message_id=user_message.id,
                assistant_message_id=None,  # No assistant response for dismissals
                answer=AssistantAnswer(
                    reply="",  # Empty reply
                    suggested_actions=[],
                    follow_up_form=None,
                ),
                form_id=None,
            )
        
        # Extract user text
        user_text = (request.text or "").strip()
        logger.info(f"User Text: {user_text[:100]}{'...' if len(user_text) > 100 else ''}")
        logger.info(f"Images Attached: {len(request.images_b64) if request.images_b64 else 0}")
        
        # Persist user message
        user_message = await self._persist_user_message(
            session_id=session_id,
            content=user_text,
            request=request,
        )
        logger.info(f"User message persisted: {user_message.id}")
        
        # Analyze images if present
        if request.images_b64:
            logger.info(f"Analyzing {len(request.images_b64)} image(s)...")
            await self._analyze_images(session_id, user_message.id, request)
        
        # Get conversation context
        context = await self._context_service.get_ai_context(session_id)
        logger.info(f"Context retrieved: {len(context.events)} events in history")
        
        # === CLASSIFY (makes all decisions) ===
        logger.info("-" * 80)
        logger.info("CLASSIFICATION PHASE")
        classification = await self._classifier.classify(
            ClassificationRequest(
                session_id=session_id,
                user_text=user_text,
                locale=request.locale,
                context=context,
            )
        )
        logger.info(f"  ├─ Intent: {classification.intent.value}")
        logger.info(f"  ├─ Next Action: {classification.next_action.value}")
        logger.info(f"  ├─ Confidence: {classification.confidence:.2f}" if classification.confidence else "  ├─ Confidence: N/A")
        if classification.problem_category_slug:
            logger.info(f"  ├─ Category: {classification.problem_category_slug}")
        if classification.problem_cause_slug:
            logger.info(f"  ├─ Cause: {classification.problem_cause_slug}")
        if classification.solution_slug:
            logger.info(f"  ├─ Solution: {classification.solution_slug}")
        logger.info(f"  └─ Reasoning: {classification.reasoning[:150]}{'...' if len(classification.reasoning) > 150 else ''}")
        
        # Log classifier usage
        if classification.usage:
            await self._log_usage(session_id, user_message.id, classification.usage)
            logger.info(f"Classifier usage: {classification.usage.total_tokens} tokens (${classification.usage.cost_total:.4f})")
        
        # === GENERATE RESPONSE (just creates text) ===
        logger.info("-" * 80)
        logger.info("RESPONSE GENERATION PHASE")
        response = await self._response_generator.generate(
            ResponseRequest(
                classification=classification,
                locale=request.locale,
            )
        )
        logger.info(f"  ├─ Reply: {response.reply[:150]}{'...' if len(response.reply) > 150 else ''}")
        if response.suggested_action:
            logger.info(f"  └─ Suggested Action: {response.suggested_action}")
        
        # Log response usage
        if response.usage:
            await self._log_usage(session_id, user_message.id, response.usage)
            logger.info(f"Response usage: {response.usage.total_tokens} tokens (${response.usage.cost_total:.4f})")
        
        # === BUILD ANSWER ===
        logger.info("-" * 80)
        logger.info("BUILDING ANSWER")
        
        # If conversation is being closed, don't suggest "Close conversation"
        suggested_actions = []
        if classification.next_action not in (NextAction.CLOSE_RESOLVED, NextAction.ESCALATE):
            if response.suggested_action:
                suggested_actions = [response.suggested_action]
        
        answer = AssistantAnswer(
            reply=response.reply,
            suggested_actions=suggested_actions,
            follow_up_form=self._form_builder.build_form(classification.next_action),
            confidence=classification.confidence,
            metadata={
                "intent": classification.intent.value,
                "next_action": classification.next_action.value,
                "reasoning": classification.reasoning,
            },
        )
        
        if answer.follow_up_form:
            logger.info(f"  └─ Form attached: {answer.follow_up_form.title}")
        
        # Persist assistant message
        assistant_message = await self._persist_assistant_message(session_id, answer)
        logger.info(f"Assistant message persisted: {assistant_message.id}")
        
        # === TRACK SOLUTION IF SUGGESTED ===
        if classification.solution_slug:
            logger.info(f"Tracking solution: {classification.solution_slug}")
            await self._track_solution(session_id, classification.solution_slug)
        
        # === UPDATE SESSION STATUS ===
        if classification.next_action == NextAction.CLOSE_RESOLVED:
            await self._session_repo.set_status(session_id, "resolved")
            logger.info("Session marked as RESOLVED")
        elif classification.next_action == NextAction.ESCALATE:
            await self._session_repo.set_status(session_id, "escalated")
            logger.info("Session marked as ESCALATED")
        else:
            await self._session_repo.touch(session_id)
        
        logger.info("=" * 80)
        logger.info("WORKFLOW COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        
        # === RETURN RESPONSE ===
        from app.data.DTO.assistant_api_dto import AssistantMessageResponse
        
        return AssistantMessageResponse(
            session_id=session_id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            answer=answer,
            form_id=None,
        )
    
    # === HELPER METHODS ===
    
    async def _get_or_create_session(self, session_id: Optional[UUID]) -> ConversationSession:
        """Get existing session or create new one."""
        if session_id:
            existing = await self._session_repo.get_by_id(session_id)
            if existing:
                return existing
            logger.warning(f"Session {session_id} not found, creating new one")
        
        return await self._session_repo.create(ConversationSession(status="in_progress"))
    
    async def _persist_user_message(
        self,
        session_id: UUID,
        content: str,
        request: UserMessageRequest,
    ) -> ConversationMessage:
        """Persist user message with image metadata."""
        # Start with metadata from the request (includes form submissions, client_hidden, etc.)
        metadata = dict(request.metadata) if request.metadata else {}
        
        if request.images_b64:
            metadata["has_images"] = True
            metadata["attachments"] = []
            
            for i, img_b64 in enumerate(request.images_b64):
                # Get the hint from the request or None
                hint = None
                if request.image_mime_types and i < len(request.image_mime_types):
                    hint = request.image_mime_types[i]
                
                # Use the utility to resolve the correct mime type
                mime_type = resolve_image_mime(hint, img_b64, logger=logger)
                
                metadata["attachments"].append({
                    "type": "image",
                    "base64": img_b64,
                    "mime_type": mime_type,
                })
        
        message = ConversationMessage(
            session_id=session_id,
            role=MessageRole.USER,
            content=content,
            message_metadata=metadata,
        )
        return await self._message_repo.create(message)
    
    async def _persist_assistant_message(
        self,
        session_id: UUID,
        answer: AssistantAnswer,
    ) -> ConversationMessage:
        """Persist assistant message."""
        from app.data.DTO.assistant_metadata_dto import AssistantMessageMetadata
        
        metadata_model = AssistantMessageMetadata.from_answer(answer)
        message = ConversationMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=answer.reply,
            message_metadata=metadata_model.to_message_metadata(),
        )
        return await self._message_repo.create(message)
    
    async def _analyze_images(self, session_id: UUID, message_id: UUID, request: UserMessageRequest):
        """Analyze images and log usage."""
        from app.data.DTO.image_analysis_dto import ImageAnalysisRequest
        
        analysis_request = ImageAnalysisRequest(
            session_id=session_id,
            message_id=message_id,
            images_b64=request.images_b64,
            image_mime_types=request.image_mime_types or [],
            locale=request.locale,
            user_prompt=request.text,
        )
        
        try:
            analysis_result = await self._image_analysis.analyze_and_store(analysis_request)
            if analysis_result.usage:
                await self._log_usage(session_id, message_id, analysis_result.usage)
        except Exception:
            logger.exception(f"Image analysis failed for session {session_id}")
    
    async def _track_solution(self, session_id: UUID, solution_slug: str):
        """Track that we suggested this solution."""
        from app.data.schemas.models import SessionSuggestion
        
        try:
            # Look up solution by slug to get its ID
            solution = await self._solution_repo.get_by_slug(solution_slug)
            if not solution:
                logger.warning(f"Solution not found for slug: {solution_slug}")
                return
            
            suggestion = SessionSuggestion(
                session_id=session_id,
                solution_id=solution.id,
            )
            await self._suggestion_repo.create(suggestion)
        except Exception:
            logger.exception(f"Failed to track solution {solution_slug}")
    
    async def _log_usage(self, session_id: UUID, message_id: UUID, usage):
        """Log AI usage to database."""
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
            await self._usage_repo.create(record)
        except Exception:
            logger.exception(f"Failed to log usage for session {session_id}")
    
    async def _mark_form_consumed(self, message_id: UUID):
        """Mark a form in an assistant message as consumed (submitted/dismissed)."""
        try:
            message = await self._message_repo.get_by_id(message_id)
            if not message:
                logger.warning(f"Message {message_id} not found for form consumption")
                return
            
            # Update metadata to mark form as consumed
            metadata = message.message_metadata or {}
            metadata["form_consumed"] = True
            message.message_metadata = metadata
            
            await self._message_repo.update(message)
            logger.info(f"Marked form in message {message_id} as consumed")
        except Exception:
            logger.exception(f"Failed to mark form consumed for message {message_id}")
