from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import get_metrics_service
from app.data.DTO.metrics_dto import UsageMetricsResponse
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/usage", response_model=UsageMetricsResponse)
async def get_usage_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service),
) -> UsageMetricsResponse:
    return await metrics_service.get_usage_summary()
