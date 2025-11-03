from __future__ import annotations

import asyncio
import json
import logging
from typing import List

from openai import OpenAI

from app.core.config import settings
from app.data.DTO import (
    AssistantAnswer,
    GeneratedForm,
    GeneratedFormField,
    GeneratedFormOption,
    ResponseGenerationRequest,
)

logger = logging.getLogger(__name__)


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
            "Use the supplied history of attempted suggested actions to avoid repeating them. "
            "If you genuinely have no fresh ideas, acknowledge it and propose escalating to a human specialist. "
            "When you are unsure, request clarifying details before guessing. "
            "You are STRICTLY limited to dishwasher issues. If the user asks about any non-dishwasher topic, refuse with a helpful reminder that you only support dishwasher troubleshooting. "
            "If the user asks about any non-dishwasher topic, refuse with a helpful reminder that you only support dishwasher troubleshooting. "
            "When refusing, set follow_up.type to 'none', leave suggested_actions empty, and provide a short apology plus offer to help with dishwasher topics instead. Do not mention policies or speculate. "
            "Example refusal JSON: {\"reply\":\"Sorry, I can only help with dishwasher troubleshooting. If you have a dishwasher question, let me know!\",\"suggested_actions\":[],\"confidence\":null,\"follow_up\":{\"type\":\"none\",\"reason\":\"Request outside dishwasher scope\"}}. "
            "Follow-up guidance: set follow_up.type to 'none' by default."
            "Always choose 'resolution_check' when the latest user input or quick checkin form summary mentions the issue is fixed, resolved or the suggestions you provided worked or helped the user. "
            "Reserve 'escalation' for cases where you lack further actionable advice or the user explicitly asks for human help. "
            "Your response MUST be raw JSON with these top-level fields: reply (string), suggested_actions (array of strings), confidence (number between 0 and 1 or null), follow_up (object or null). "
            "The follow_up object MUST contain: type (one of none, resolution_check, escalation), reason (short string explaining why)"
            "Never include markdown code fences or additional commentary."
        )

        context_sections = self._build_context_blocks(request)

        return self._client.responses.create(
            model=self._model,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": context_sections,
                },
            ],
            temperature=0.4,
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
        raw_text = self._extract_text(response)
        payload = self._coerce_json(raw_text)

        reply = str(payload.get("reply") or raw_text or "I ran into an issue generating a reply.")
        action_payload = payload.get("suggested_actions")
        suggested_actions = self._ensure_list_of_str(action_payload)

        follow_up_payload = payload.get("follow_up")
        follow_up_type = None
        follow_up_reason = None

        if isinstance(follow_up_payload, dict):
            follow_up_type = str(
                follow_up_payload.get("type")
                or follow_up_payload.get("action")
                or ""
            ).strip() or None
            reason_value = follow_up_payload.get("reason")
            follow_up_reason = (
                str(reason_value).strip() if isinstance(reason_value, str) and reason_value.strip() else None
            )
        else:
            legacy_type = payload.get("follow_up_type") or payload.get("follow_up_action")
            if isinstance(legacy_type, str) and legacy_type.strip():
                follow_up_type = legacy_type.strip()
            legacy_reason = payload.get("follow_up_reason")
            if isinstance(legacy_reason, str) and legacy_reason.strip():
                follow_up_reason = legacy_reason.strip()
        follow_up_form = None

        confidence_value = payload.get("confidence")
        try:
            confidence = float(confidence_value)
        except (TypeError, ValueError):
            confidence = None

        if confidence is not None:
            confidence = max(0.0, min(confidence, 1.0))

        metadata = {
            k: v
            for k, v in payload.items()
            if k
            not in {"reply", "suggested_actions", "follow_up", "follow_up_form", "follow_up_action", "follow_up_type", "follow_up_reason", "confidence"}
        }

        return AssistantAnswer(
            reply=reply,
            suggested_actions=suggested_actions,
            follow_up_form=follow_up_form,
            confidence=confidence,
            metadata=metadata,
            follow_up_type=follow_up_type,
            follow_up_reason=follow_up_reason,
        )

    @staticmethod
    def _extract_text(response) -> str:
        chunks: List[str] = []
        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) == "output_text":
                chunks.append(getattr(item, "text", ""))
        if not chunks and hasattr(response, "output_text"):
            chunks.append(getattr(response, "output_text", ""))
        return "".join(chunks).strip()

    @staticmethod
    def _coerce_json(text: str) -> dict:
        if not text:
            return {}
        cleaned = ResponseGenerationService._strip_code_fence(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse assistant JSON response: %s", text)
            return {}

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        snippet = text.strip()
        if not snippet.startswith("```"):
            return snippet

        lines = snippet.splitlines()
        if not lines:
            return snippet

        # Drop opening fence (e.g., ``` or ```json)
        if lines[0].startswith("```"):
            lines = lines[1:]

        # Drop trailing fence if present
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        return "\n".join(lines).strip()

    def _parse_form(self, payload) -> GeneratedForm | None:
        if not isinstance(payload, dict):
            return None

        fields_payload = payload.get("fields") or []
        fields: List[GeneratedFormField] = []
        for item in fields_payload:
            if not isinstance(item, dict):
                continue
            options_payload = item.get("options") or []
            options = [
                GeneratedFormOption(
                    value=str(option.get("value", option.get("label", "option"))),
                    label=str(option.get("label", option.get("value", "Option"))),
                )
                for option in options_payload
                if isinstance(option, dict)
            ]
            fields.append(
                GeneratedFormField(
                    question=str(item.get("question", item.get("label", ""))),
                    input_type=str(item.get("type", "text")),
                    required=bool(item.get("required", False)),
                    placeholder=item.get("placeholder"),
                    options=options,
                )
            )

        if not fields:
            return None

        return GeneratedForm(
            title=str(payload.get("title", "Additional details")),
            description=payload.get("description"),
            fields=fields,
        )

    @staticmethod
    def _ensure_list_of_str(value) -> List[str]:
        if isinstance(value, list):
            cleaned: List[str] = []
            for item in value:
                if not isinstance(item, str):
                    item = str(item)
                text = item.strip()
                if text:
                    cleaned.append(text)
            return cleaned
        if value:
            return [str(value).strip()]
        return []
