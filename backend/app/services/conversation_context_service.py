from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from app.data.repositories import ConversationSessionRepository, ConversationImageRepository
from app.data.schemas.models import MessageRole
from app.data.DTO.conversation_context_dto import ConversationAIContext


class ConversationContextService:
    """Create concise conversation context payloads for downstream AI calls."""

    def __init__(
        self,
        session_repository: ConversationSessionRepository,
        image_repository: ConversationImageRepository,
    ) -> None:
        self._session_repository = session_repository
        self._image_repository = image_repository

    async def get_ai_context(self, session_id: UUID) -> ConversationAIContext:
        """Return a trimmed conversation context for downstream AI calls.

        We keep only the essential timeline: user inputs, submitted form outcomes,
        assistant suggested actions, and image analysis results.
        """

        aggregate = await self._session_repository.get_context(session_id)
        if not aggregate:
            return ConversationAIContext(session_id=session_id)

        event_records: List[Tuple[Optional[datetime], int, str]] = []
        order = 0

        def add_event(text: Optional[str], timestamp: Optional[datetime]) -> None:
            nonlocal order
            if not text:
                return
            formatted = self._format_with_timestamp(text, timestamp)
            event_records.append((timestamp, order, formatted))
            order += 1

        for message in aggregate.get("messages") or []:
            role = getattr(message, "role", None)
            created_at = getattr(message, "created_at", None)
            metadata = getattr(message, "message_metadata", {}) or {}

            if role == MessageRole.USER:
                normalized = self._normalize_text(message.content)
                if normalized:
                    add_event(f"User: {normalized}", created_at)
                for form_event in self._extract_form_events(metadata):
                    add_event(form_event, created_at)
            elif role == MessageRole.ASSISTANT:
                assistant_entry = self._format_suggested_actions(metadata)
                if assistant_entry:
                    add_event(assistant_entry, created_at)
                for form_event in self._extract_form_events(metadata):
                    add_event(form_event, created_at)

        for timestamp, text in await self._build_image_events(session_id):
            add_event(text, timestamp)

        event_records.sort(key=lambda item: (self._normalize_timestamp(item[0]), item[1]))
        ordered_events = [text for _, _, text in event_records]

        return ConversationAIContext(
            session_id=session_id,
            events=self._trim_events(ordered_events),
        )

    @staticmethod
    def _normalize_text(value: Optional[str]) -> Optional[str]:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned or None

    def _format_suggested_actions(self, metadata: dict) -> Optional[str]:
        actions = self._collect_actions(metadata)
        if not actions:
            return None
        return "Assistant suggested: " + "; ".join(actions)

    def _extract_form_events(self, metadata: dict) -> List[str]:
        if not isinstance(metadata, dict):
            return []

        events: List[str] = []

        summary = metadata.get("follow_up_form_summary")
        if not summary:
            extra = metadata.get("extra")
            if isinstance(extra, dict):
                summary = extra.get("form_summary")
        if isinstance(summary, str):
            summary_clean = summary.strip()
            if summary_clean:
                events.append(f"Form submission: {summary_clean}")

        submission = metadata.get("follow_up_form_submission") or metadata.get("follow_up_form_response")
        if isinstance(submission, dict):
            status = submission.get("status")
            choice = submission.get("choice") or submission.get("value") or submission.get("answer")
            detail_parts: List[str] = []
            if isinstance(status, str) and status.strip():
                detail_parts.append(status.strip())
            if isinstance(choice, str) and choice.strip():
                detail_parts.append(choice.strip())
            if detail_parts and not summary:
                events.append("Form submission: " + " - ".join(detail_parts))

        return events

    async def _build_image_events(self, session_id: UUID) -> List[Tuple[Optional[datetime], str]]:
        events: List[Tuple[Optional[datetime], str]] = []
        try:
            images = await self._image_repository.list_by_session(session_id=session_id, limit=500)
        except Exception:  # noqa: BLE001
            return events

        seen: set[str] = set()
        for image in images:
            summary = (image.analysis_text or "").strip()
            if not summary:
                continue
            key = summary.casefold()
            if key in seen:
                continue
            seen.add(key)

            details: List[str] = []
            metadata = image.analysis_metadata or {}
            if isinstance(metadata, dict):
                condition = metadata.get("condition")
                detail_source = metadata.get("details")
                if isinstance(detail_source, list):
                    details = [str(item).strip() for item in detail_source if str(item).strip()]
                elif isinstance(detail_source, str) and detail_source.strip():
                    details = [detail_source.strip()]

            tag = None
            if condition and isinstance(condition, str) and condition.strip():
                tag = condition.strip().lower()

            description = summary
            if details:
                description = f"{summary} (Image details: {'; '.join(details[:4])})"
            if tag:
                description = f"[{tag}] {description}"

            events.append((getattr(image, "created_at", None), f"Image analysis: {description}"))

        return events

    @staticmethod
    def _ensure_list(value) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if value is None:
            return []
        text = str(value).strip()
        return [text] if text else []

    def _collect_actions(self, metadata: dict) -> List[str]:
        combined: List[str] = []
        seen: set[str] = set()

        source = metadata.get("suggested_actions")
        for item in self._ensure_list(source):
            lowered = item.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            combined.append(item)

        return combined

    @staticmethod
    def _format_with_timestamp(text: str, timestamp: Optional[datetime]) -> str:
        if not isinstance(timestamp, datetime):
            return text
        ts = timestamp
        if ts.tzinfo is not None:
            ts = ts.astimezone(timezone.utc)
        return f"[{ts.strftime('%Y-%m-%d %H:%M')} UTC] {text}"

    @staticmethod
    def _normalize_timestamp(value: Optional[datetime]) -> datetime:
        if isinstance(value, datetime):
            ts = value
            if ts.tzinfo is not None:
                ts = ts.astimezone(timezone.utc)
            return ts.replace(tzinfo=None)
        return datetime.min

    @staticmethod
    def _trim_events(events: List[str], limit: int = 30) -> List[str]:
        if len(events) <= limit:
            return events
        return events[-limit:]


