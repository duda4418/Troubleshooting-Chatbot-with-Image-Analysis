from __future__ import annotations

import json
from typing import List, Optional
from uuid import UUID

from app.data.repositories import ConversationSessionRepository
from app.data.schemas.models import MessageRole
from app.data.DTO.conversation_context_dto import ConversationAIContext


class ConversationContextService:
    """Create concise conversation context payloads for downstream AI calls."""

    def __init__(self, session_repository: ConversationSessionRepository) -> None:
        self._session_repository = session_repository

    async def get_ai_context(self, session_id: UUID) -> ConversationAIContext:
        """Return sanitized conversation details for the given session.

        The response captures only the information the OpenAI Responses API needs:
        user-authored messages, image analysis notes, assistant replies with
        metadata, and answered form prompts rendered as succinct events.
        """

        aggregate = await self._session_repository.get_context(session_id)
        if not aggregate:
            return ConversationAIContext(session_id=session_id)

        events: List[str] = []

        for message in aggregate.get("messages") or []:
            role = getattr(message, "role", None)
            if role == MessageRole.USER:
                normalized = self._normalize_text(message.content)
                if normalized:
                    events.append(f"User message: {normalized}")
            elif role == MessageRole.ASSISTANT:
                assistant_entry = self._format_assistant_event(message)
                if assistant_entry:
                    events.append(assistant_entry)

        events.extend(self._build_image_events(aggregate.get("image_descriptions")))
        events.extend(self._build_form_events(aggregate.get("forms")))

        return ConversationAIContext(
            session_id=session_id,
            events=self._trim_events(events),
        )

    @staticmethod
    def _normalize_text(value: Optional[str]) -> Optional[str]:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned or None

    def _format_assistant_event(self, message) -> Optional[str]:
        reply = self._normalize_text(getattr(message, "content", None))
        metadata = getattr(message, "message_metadata", {}) or {}

        parts: List[str] = []
        if reply:
            parts.append(f"Assistant reply: {reply}")

        suggestions = self._ensure_list(metadata.get("suggestions"))
        if suggestions:
            parts.append("Suggestions: " + "; ".join(suggestions))

        actions = self._ensure_list(metadata.get("actions"))
        if actions:
            parts.append("Actions: " + "; ".join(actions))

        follow_up_form = metadata.get("follow_up_form")
        if isinstance(follow_up_form, dict):
            title = follow_up_form.get("title") or "Follow-up form"
            parts.append(f"Offered form: {title}")

        form_summary = metadata.get("extra", {}).get("form_summary")
        if isinstance(form_summary, str) and form_summary.strip():
            parts.append(f"Form summary: {form_summary.strip()}")

        additional = self._summarize_metadata(metadata)
        if additional:
            parts.append(f"Metadata: {additional}")

        if not parts:
            return None

        return "\n".join(parts)

    def _build_image_events(self, descriptions) -> List[str]:
        events: List[str] = []
        if not isinstance(descriptions, list):
            return events

        for index, desc in enumerate(descriptions, start=1):
            if not isinstance(desc, str):
                continue
            cleaned = desc.strip()
            if not cleaned:
                continue
            events.append(f"Image analysis {index}: {cleaned}")
        return events

    def _build_form_events(self, forms) -> List[str]:
        events: List[str] = []
        if not isinstance(forms, list):
            return events

        for form in forms:
            if not isinstance(form, dict):
                continue
            title = (form.get("title") or "Follow-up form").strip() or "Follow-up form"
            status = form.get("status") or "in_progress"
            prefix = f"Form '{title}' [{status}]"
            for item in form.get("inputs", []) or []:
                question = self._normalize_text(item.get("question")) or "Prompt"
                answer = self._normalize_text(item.get("answer"))
                if not answer:
                    continue
                events.append(f"{prefix} prompt '{question}': {answer}")
        return events

    @staticmethod
    def _ensure_list(value) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if value is None:
            return []
        text = str(value).strip()
        return [text] if text else []

    @staticmethod
    def _trim_events(events: List[str], limit: int = 30) -> List[str]:
        if len(events) <= limit:
            return events
        return events[-limit:]

    @staticmethod
    def _summarize_metadata(metadata: dict) -> Optional[str]:
        if not isinstance(metadata, dict):
            return None

        ignore_keys = {"suggestions", "actions", "follow_up_form"}
        condensed: dict[str, object] = {}

        for key, value in metadata.items():
            if key in ignore_keys:
                continue
            if value in (None, "", [], {}):
                continue
            if key == "extra" and isinstance(value, dict):
                for extra_key, extra_value in value.items():
                    if extra_value in (None, "", [], {}):
                        continue
                    condensed[f"extra.{extra_key}"] = extra_value
                continue
            condensed[key] = value

        if not condensed:
            return None

        pieces: List[str] = []
        for key, value in condensed.items():
            if isinstance(value, (dict, list)):
                snippet = json.dumps(value, ensure_ascii=False)
                if len(snippet) > 160:
                    snippet = snippet[:157] + "..."
            else:
                snippet = str(value)
            pieces.append(f"{key}: {snippet}")

        return "; ".join(pieces)

