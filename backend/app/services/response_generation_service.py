from __future__ import annotations

import asyncio
import logging
from typing import List, Optional, Literal

from openai import OpenAI

from app.core.config import settings
from app.data.DTO import AssistantAnswer, ResponseGenerationRequest
from app.data.DTO.usage_dto import ModelUsageDetails
from app.services.utils.usage_metrics import embed_usage_metadata, extract_usage_details
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class FollowUpPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["none", "resolution_check", "escalation"] = Field(
        description="Default 'none'. If the user's need seems resolved use 'resolution_check' to check if the problem was fixed completely. 'escalation' only if human help seems necessary."
    )
    reason: str = Field(
        description="One-sentence justification for the chosen type. If type is 'none', explain briefly why no follow-up is needed."
    )

class AssistantResponsePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reply: str = Field(description="Final user-facing message. Keep it very, very short, concise and directly helpful. Can use markdown, and if lists are used, then use bulletpoints")
    suggested_actions: List[str] = Field(
        default_factory=list,
        description="Very short concise summaries of the suggestions presented in the reply. If no suggestions were made, return an empty list []."
    )
    confidence: float = Field(
        ..., ge=0, le=1,
        description="Model's confidence in the reply."
    )
    follow_up: Optional[FollowUpPayload] = Field(
        None,
        description="If unsure, set to null. Avoid guessing."
    )


class ResponseGenerationResult(BaseModel):
    answer: AssistantAnswer
    usage: Optional[ModelUsageDetails] = None


class ResponseGenerationService:
    """Call OpenAI Responses API to craft assistant replies using conversation context."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        response_model: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = response_model or settings.OPENAI_RESPONSE_MODEL
        self._client = OpenAI(api_key=self._api_key) if self._api_key else None

    async def generate(self, request: ResponseGenerationRequest) -> ResponseGenerationResult:
        if not self._client:
            raise RuntimeError("OpenAI API key is not configured")

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: self._invoke_openai(request))
        answer = self._parse_response(response)
        usage_details = extract_usage_details(
            response,
            default_model=self._model,
            request_type="response_generation",
        )
        if usage_details:
            answer.metadata = embed_usage_metadata(answer.metadata, usage_details)
        return ResponseGenerationResult(answer=answer, usage=usage_details)

    def _invoke_openai(self, request: ResponseGenerationRequest):
        system_prompt = (
            "You are a friendly dishwasher troubleshooting assistant. Stay practical, very short, concise, and informal without repeating yourself. "
            "Try to understand the user's problem first, if unclear, ask clarifying questions. "
            "Use the supplied history of attempted suggested actions to avoid repeating them. "
            "Propose very few short targeted solutions based on the user's problem and context. "
            "If you do not understand what the user is asking or the context is unclear, ask for clarification instead of guessing. "
            "If you genuinely have no fresh ideas, acknowledge it and propose escalating to a human specialist. "
            "If you already suggested the options from the dishwasher troubleshooting manual, do not repeat them; instead, acknowledge it and suggest escalation. stop giving other suggestions unless the user provides more information that could help find a new lead. "
            "You have an internal tool that escalates the problem to a human specialist when needed. Use it wisely."

            "Follow-up guidance: set follow_up.type to 'none' by default."
            "Choose 'resolution_check' when the latest user input or quick checkin form summary mentions the issue is fixed, resolved or the user mentions the suggestions worked. This is not for checking if things helped, but if the issue appears resolved. "
            "Reserve 'escalation' for cases where you lack further actionable advice or the user explicitly asks for human help. "
            
            "When you are unsure, or the user input does not make sense, request clarifying details before guessing. "
            "You are STRICTLY limited to dishwasher issues. If the user asks about any non-dishwasher topic, refuse with a helpful reminder that you only support dishwasher troubleshooting. "
            "If the user asks about any non-dishwasher topic, refuse with a helpful reminder that you only support dishwasher troubleshooting. "
            "When refusing, set follow_up.type to 'none', leave suggested_actions empty, and provide a short apology plus offer to help with dishwasher topics instead. Do not mention policies or speculate. "

            "Avoid repeating suggestions or advice already given in the context. "
            "Never include markdown code fences or additional commentary. "
        )

        content_blocks = self._build_context_blocks(request)
        self._log_prompt_preview(request, system_prompt, content_blocks)

        return self._client.responses.parse(
            model=self._model,
            instructions=system_prompt,
            input=[{"role": "user", "content": content_blocks}],
            #reasoning={"effort": "minimal"},
            #text={"verbosity": "low"},
            temperature=0.2,
            text_format=AssistantResponsePayload,
        )

    def _build_context_blocks(self, request: ResponseGenerationRequest) -> List[dict]:
        blocks: List[dict] = []
        context = request.context

        locale_value = request.locale or "unknown"
        summary_lines: List[str] = [f"Locale: {locale_value}"]
        if request.user_text:
            summary_lines.append(f"Latest user input: {request.user_text}")

        event_lines = context.events[-15:] if context.events else []
        if event_lines:
            bullet_history = "\n".join(f"- {line}" for line in event_lines)
            summary_lines.append("Conversation context:\n" + bullet_history)
        else:
            summary_lines.append("Conversation context is currently empty.")

        if request.recommendation_summary:
            summary_lines.append(
                "Avoid repeating these troubleshooting attempts:\n" + request.recommendation_summary
            )

        if request.knowledge_hits:
            knowledge_lines: List[str] = []
            for hit in request.knowledge_hits[:3]:
                steps_text = "; ".join(hit.steps)
                entry = f"- {hit.label}: {hit.summary}"
                if steps_text:
                    entry = f"{entry} | Suggested steps: {steps_text}"
                knowledge_lines.append(entry)
            summary_lines.append(
                "Suggestions from dishwasher troubleshooting manual:\n" + "\n".join(knowledge_lines)
            )

        blocks.append({"type": "input_text", "text": "\n\n".join(summary_lines)})

        return blocks

    def _log_prompt_preview(
        self,
        request: ResponseGenerationRequest,
        instructions: str,
        content_blocks: List[dict],
    ) -> None:
        session_identifier = getattr(request, "session_id", None)
        header = "Responses prompt preview"
        if session_identifier:
            header = f"{header} (session {session_identifier})"

        lines: List[str] = ["=== Instructions ===", instructions.strip(), "=== User Content Blocks ==="]

        for index, block in enumerate(content_blocks, start=1):
            block_type = block.get("type", "unknown")
            lines.append(f"[Block {index} | type={block_type}]")
            if block_type == "input_text":
                lines.append(block.get("text", ""))
            else:
                lines.append(repr(block))

        preview = "\n".join(lines)
        print(f"{header}\n{preview}")
        logger.info("%s\n%s", header, preview)

    def _parse_response(self, response) -> AssistantAnswer:
        payload = getattr(response, "output_parsed", None)
        if not isinstance(payload, AssistantResponsePayload):
            message = "OpenAI response did not include the expected structured payload"
            logger.error(message)
            raise RuntimeError(message)

        return self._from_typed_payload(payload)

    def _from_typed_payload(self, payload: AssistantResponsePayload) -> AssistantAnswer:
        reply = payload.reply.strip() if payload.reply else ""
        actions = [action.strip() for action in payload.suggested_actions if action and action.strip()]

        follow_up_type = None
        follow_up_reason = None
        if payload.follow_up:
            follow_up_type = payload.follow_up.type.strip()
            follow_up_reason = payload.follow_up.reason.strip() or None
            if not follow_up_type:
                follow_up_type = None

        confidence = payload.confidence
        if confidence is not None:
            try:
                confidence = max(0.0, min(float(confidence), 1.0))
            except (TypeError, ValueError):
                confidence = None

        metadata = {}
        extra = getattr(payload, "model_extra", None)
        if isinstance(extra, dict):
            metadata = {
                k: v
                for k, v in extra.items()
                if k not in {"reply", "suggested_actions", "confidence", "follow_up"}
            }

        return AssistantAnswer(
            reply=reply or "",
            suggested_actions=actions,
            follow_up_form=None,
            confidence=confidence,
            metadata=metadata,
            follow_up_type=follow_up_type,
            follow_up_reason=follow_up_reason,
        )
