from __future__ import annotations

import logging
from typing import Dict, List
from uuid import UUID

from app.core.config import settings
from app.data.DTO.metrics_dto import (
    FeedbackMetrics,
    SessionUsageMetrics,
    UsageMetricsResponse,
    UsageTotals,
)
from app.data.repositories import (
    ConversationMessageRepository,
    ConversationSessionRepository,
    ModelUsageRepository,
)
from app.data.schemas.models import ConversationSession

logger = logging.getLogger(__name__)


class MetricsService:
    """Aggregate usage, cost, and feedback metrics for dashboards."""

    def __init__(
        self,
        *,
        session_repository: ConversationSessionRepository,
        message_repository: ConversationMessageRepository,
        usage_repository: ModelUsageRepository,
    ) -> None:
        self._session_repository = session_repository
        self._message_repository = message_repository
        self._usage_repository = usage_repository

    async def get_usage_summary(self) -> UsageMetricsResponse:
        totals_raw = await self._usage_repository.aggregate_totals()
        session_rows = await self._usage_repository.aggregate_by_session()

        session_ids: List[UUID] = [row["session_id"] for row in session_rows if row.get("session_id")]
        session_map: Dict[UUID, ConversationSession] = {}
        message_counts: Dict[UUID, int] = {}

        if session_ids:
            sessions = await self._session_repository.get_many(session_ids)
            session_map = {session.id: session for session in sessions}
            message_counts = await self._message_repository.count_by_sessions(session_ids)
        session_metrics: List[SessionUsageMetrics] = []
        for row in session_rows:
            session_id = row.get("session_id")
            session = session_map.get(session_id)
            if not session:
                logger.debug("Skipping usage row for missing session %s", session_id)
                continue
            session_metrics.append(
                SessionUsageMetrics(
                    session_id=session_id,
                    status=session.status,
                    updated_at=session.updated_at,
                    messages=message_counts.get(session_id, 0),
                    usage_records=row.get("usage_records", 0),
                    input_tokens=row.get("input_tokens", 0),
                    output_tokens=row.get("output_tokens", 0),
                    total_tokens=row.get("total_tokens", 0),
                    cost_input=row.get("cost_input", 0.0),
                    cost_output=row.get("cost_output", 0.0),
                    cost_total=row.get("cost_total", 0.0),
                    feedback_rating=session.feedback_rating,
                )
            )

        session_metrics.sort(key=lambda item: item.updated_at, reverse=True)

        totals = UsageTotals(
            usage_records=totals_raw.get("usage_records", 0),
            sessions=totals_raw.get("sessions", 0),
            input_tokens=totals_raw.get("input_tokens", 0),
            output_tokens=totals_raw.get("output_tokens", 0),
            total_tokens=totals_raw.get("total_tokens", 0),
            cost_input=totals_raw.get("cost_input", 0.0),
            cost_output=totals_raw.get("cost_output", 0.0),
            cost_total=totals_raw.get("cost_total", 0.0),
        )

        average_rating, rated_sessions = await self._session_repository.get_feedback_stats()
        feedback = FeedbackMetrics(
            average_rating=average_rating,
            rated_sessions=rated_sessions,
        )

        return UsageMetricsResponse(
            totals=totals,
            sessions=session_metrics,
            feedback=feedback,
            pricing_configured=bool(settings.openai_pricing),
        )
