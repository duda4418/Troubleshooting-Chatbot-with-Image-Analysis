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
            "You are a focused dishwasher troubleshooting assistant. Keep replies short, direct, and conversational. "
            "When the classifier provides clarifying next_questions, ask at most one concise follow-up per turn and only when it drives the diagnosis forward. "
            "If you also receive a new solution, share the actionable step first, then ask the follow-up question. When no new solutions are available, combine the clarifying need with a brief diagnostic tip so the user can still make progress. "
            "Avoid repeating identical guidance unless the user specifically requests it, and reference prior attempts when offering an alternative. "
            "If the plan notes indicate escalation, all steps are exhausted, or the user explicitly asks for human help, guide the user toward escalation instead of inventing new fixes. "
            "Stay strictly within dishwasher troubleshooting. If the topic is outside scope, refuse with a short apology and invite dishwasher questions. "
            "Follow-up guidance: default follow_up.type to 'none'. Use 'resolution_check' only when the user explicitly states the issue seems resolved. Use 'escalation' when escalation is recommended, the planner escalates, or the user explicitly asks for human assistance. "
            "Never include code fences or policy discussion. Avoid repeating the same advice across consecutive messages. "
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
        summary_lines: List[str] = []

        locale_value = request.locale or "unknown"
        summary_lines.append(f"Locale: {locale_value}")
        if request.user_text:
            summary_lines.append(f"Latest user input: {request.user_text}")
        else:
            summary_lines.append("Latest user input: <none provided>")

        event_lines = context.events[-15:] if context.events else []
        if event_lines:
            bullet_history = "\n".join(f"- {line}" for line in event_lines)
            summary_lines.append("Recent conversation events:\n" + bullet_history)
        else:
            summary_lines.append("No prior conversation events available.")

        classification = request.classification
        classification_lines: List[str] = ["Classifier summary:"]
        if classification.category:
            classification_lines.append(
                f"- Category: {classification.category.slug} – {classification.category.name}"
            )
        if classification.cause:
            classification_lines.append(
                f"- Cause: {classification.cause.slug} – {classification.cause.name}"
            )
        if classification.confidence is not None:
            classification_lines.append(f"- Confidence: {classification.confidence:.2f}")
        if classification.rationale:
            classification_lines.append(f"- Rationale: {classification.rationale}")
        if classification.needs_more_info:
            classification_lines.append("- Needs more info before proposing fixes.")
        if classification.next_questions:
            classification_lines.append("- Clarifying questions to ask:")
            for question in classification.next_questions[:3]:
                classification_lines.append(f"  • {question}")
        if classification.escalate:
            reason = classification.escalate_reason or "No reason provided"
            classification_lines.append(f"- Escalation requested: {reason}")
        if classification.request_type:
            classification_lines.append(f"- Request type: {classification.request_type}")
        summary_lines.append("\n".join(classification_lines))

        plan = request.suggestion_plan
        plan_lines: List[str] = ["Planner output:"]
        if plan.escalate:
            plan_lines.append("- Planner recommends escalation. Provide human escalation guidance.")
        if plan.notes:
            plan_lines.append(f"- Notes: {plan.notes}")
        if plan.solutions:
            plan_lines.append("- Proposed solutions:")
            for item in plan.solutions:
                marker = "already suggested" if item.already_suggested else "new"
                instructions = item.solution.instructions.strip().replace("\n", " ")
                if len(instructions) > 320:
                    instructions = instructions[:317].rstrip() + "..."
                plan_lines.append(
                    f"  • {item.solution.title} ({marker})\n    Steps: {instructions}"
                )
        else:
            plan_lines.append("- No actionable solutions identified.")
        summary_lines.append("\n".join(plan_lines))

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
