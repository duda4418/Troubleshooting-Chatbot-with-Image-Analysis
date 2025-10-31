from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional
from uuid import UUID

from app.data.repositories import ConversationMessageRepository
from app.data.schemas.models import ConversationMessage, MessageRole


@dataclass
class RecommendationRecord:
    text: str
    count: int = 0


@dataclass
class RecommendationHistory:
    actions: Dict[str, RecommendationRecord] = field(default_factory=dict)

    def normalized_actions(self) -> set[str]:
        return set(self.actions.keys())

    def total_recommendations(self) -> int:
        return sum(record.count for record in self.actions.values())

    def is_empty(self) -> bool:
        return not self.actions

    def context_summary(self) -> Optional[str]:
        if self.is_empty():
            return None

        lines: List[str] = []
        if self.actions:
            lines.append("Suggested actions already attempted:")
            lines.extend(self._format_records(self.actions.values()))
        return "\n".join(lines)

    @staticmethod
    def _format_records(records: Iterable[RecommendationRecord]) -> List[str]:
        formatted: List[str] = []
        for record in records:
            suffix = f" (x{record.count})" if record.count > 1 else ""
            formatted.append(f"- {record.text}{suffix}")
        return formatted


class RecommendationTracker:
    """Aggregate past assistant suggested actions for a session."""

    def __init__(self, message_repository: ConversationMessageRepository, *, fetch_limit: int = 200) -> None:
        self._message_repository = message_repository
        self._fetch_limit = fetch_limit

    async def build_history(self, session_id: UUID) -> RecommendationHistory:
        messages = await self._message_repository.list_by_session(session_id=session_id, limit=self._fetch_limit)
        return self._aggregate(messages)

    def _aggregate(self, messages: Iterable[ConversationMessage]) -> RecommendationHistory:
        history = RecommendationHistory()
        for message in messages:
            if message.role != MessageRole.ASSISTANT:
                continue
            metadata = message.message_metadata or {}
            actions = self._collect_actions(metadata)
            if actions:
                self._record(history.actions, actions)
        return history

    @staticmethod
    def _collect_actions(metadata) -> List[str]:
        combined: List[str] = []
        if not isinstance(metadata, dict):
            return combined

        raw = metadata.get("suggested_actions")
        if isinstance(raw, list):
            for item in raw:
                text = str(item).strip()
                if text:
                    combined.append(text)
        elif isinstance(raw, str):
            text = raw.strip()
            if text:
                combined.append(text)
        return combined

    @staticmethod
    def _record(store: Dict[str, RecommendationRecord], values) -> None:
        if not isinstance(values, list):
            return
        for raw in values:
            if not isinstance(raw, str):
                continue
            normalized = RecommendationTracker._normalize(raw)
            if not normalized:
                continue
            entry = store.setdefault(normalized, RecommendationRecord(text=raw.strip(), count=0))
            entry.count += 1

    @staticmethod
    def _normalize(value: str) -> str:
        return value.strip().lower()
