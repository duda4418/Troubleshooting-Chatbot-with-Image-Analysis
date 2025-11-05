from __future__ import annotations

import asyncio
import logging
from typing import List, Optional
from typing import Literal

from openai import OpenAI

from app.core.config import settings
from app.data.DTO import AssistantAnswer, ResponseGenerationRequest
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
    reply: str = Field(description="Final user-facing message. Keep it concise and directly helpful.")
    suggested_actions: List[str] = Field(
        default_factory=list,
        description="Zero or more concrete next steps for the user. Return [] if none."
    )
    confidence: Optional[float] = Field(
        None, ge=0, le=1,
        description="Model's confidence in the reply."
    )
    follow_up: Optional[FollowUpPayload] = Field(
        None,
        description="If unsure, set to null. Avoid guessing."
    )


class ResponseGenerationService:
    """Call OpenAI Responses API to craft assistant replies using conversation context."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        reasoning_model: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = reasoning_model or settings.OPENAI_VISION_MODEL
        self._client = OpenAI(api_key=self._api_key) if self._api_key else None

    async def generate(self, request: ResponseGenerationRequest) -> AssistantAnswer:
        if not self._client:
            raise RuntimeError("OpenAI API key is not configured")

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: self._invoke_openai(request))
        return self._parse_response(response)

    def _invoke_openai(self, request: ResponseGenerationRequest):
        system_prompt = (
            "You are a friendly dishwasher troubleshooting assistant. Stay practical, concise, and informal without repeating yourself. "
            "Use the supplied history of attempted suggested actions to avoid repeating them. You use a knowledge base of dishwasher troubleshooting steps to help the user resolve their issue. "
            "If you genuinely have no fresh ideas or proposed all the knowledge steps, acknowledge it and propose escalating to a human specialist. "
            "When you are unsure, request clarifying details before guessing. "
            "You are STRICTLY limited to dishwasher issues. If the user asks about any non-dishwasher topic, refuse with a helpful reminder that you only support dishwasher troubleshooting. "
            "If the user asks about any non-dishwasher topic, refuse with a helpful reminder that you only support dishwasher troubleshooting. "
            "When refusing, set follow_up.type to 'none', leave suggested_actions empty, and provide a short apology plus offer to help with dishwasher topics instead. Do not mention policies or speculate. "
            "Example refusal JSON: {\"reply\":\"Sorry, I can only help with dishwasher troubleshooting. If you have a dishwasher question, let me know!\",\"suggested_actions\":[],\"confidence\":null,\"follow_up\":{\"type\":\"none\",\"reason\":\"Request outside dishwasher scope\"}}. "
            "Follow-up guidance: set follow_up.type to 'none' by default."
            "Choose 'resolution_check' when the latest user input or quick checkin form summary mentions the issue is fixed, resolved or the user mentions the suggestions you provided worked. This is not for checking if things helped, but if the issue appears resolved. "
            "Reserve 'escalation' for cases where you lack further actionable advice or the user explicitly asks for human help. "
            "Never include markdown code fences or additional commentary."
        )

        return self._client.responses.parse(
            model=self._model,
            instructions=system_prompt,
            input=[{"role": "user", "content": self._build_context_blocks(request)}],
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
            knowledge_lines = []
            for hit in request.knowledge_hits[:3]:
                knowledge_lines.append(
                    f"{hit.label} (score {hit.similarity:.2f}): {hit.summary}. Steps: {'; '.join(hit.steps)}"
                )
            summary_lines.append("Knowledge hits:\n" + "\n".join(knowledge_lines))

        blocks.append({"type": "input_text", "text": "\n\n".join(summary_lines)})

        return blocks

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
