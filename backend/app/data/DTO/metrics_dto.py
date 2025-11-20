from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UsageTotals(BaseModel):
    """Aggregated usage totals across all sessions."""

    usage_records: int = 0
    sessions: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_input: float = 0.0
    cost_output: float = 0.0
    cost_total: float = 0.0
    currency: str = "USD"


class SessionUsageMetrics(BaseModel):
    """Per-session usage metrics for dashboard displays."""

    session_id: UUID
    status: str
    updated_at: datetime
    messages: int = 0
    usage_records: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_input: float = 0.0
    cost_output: float = 0.0
    cost_total: float = 0.0
    feedback_rating: Optional[int] = None


class FeedbackMetrics(BaseModel):
    average_rating: Optional[float] = Field(default=None, description="Average rating across completed sessions.")
    rated_sessions: int = 0


class UsageMetricsResponse(BaseModel):
    totals: UsageTotals
    sessions: List[SessionUsageMetrics] = Field(default_factory=list)
    feedback: FeedbackMetrics
    pricing_configured: bool = False
