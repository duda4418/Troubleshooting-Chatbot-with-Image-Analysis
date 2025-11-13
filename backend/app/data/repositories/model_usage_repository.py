from __future__ import annotations

from typing import Dict, List

from sqlalchemy import distinct, func
from sqlmodel import select

from app.core.database import DatabaseProvider
from app.data.repositories.base_repository import BaseRepository
from app.data.schemas.models import ModelUsageLog


class ModelUsageRepository(BaseRepository[ModelUsageLog]):
    """Persistence layer for model usage audit logs."""

    def __init__(self, db_provider: DatabaseProvider):
        super().__init__(db_provider, ModelUsageLog)

    async def aggregate_totals(self) -> Dict[str, float]:
        async with self.db_provider.get_session() as session:
            stmt = select(
                func.count(ModelUsageLog.id).label("usage_records"),
                func.count(distinct(ModelUsageLog.session_id)).label("sessions"),
                func.coalesce(func.sum(ModelUsageLog.input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(ModelUsageLog.output_tokens), 0).label("output_tokens"),
                func.coalesce(func.sum(ModelUsageLog.total_tokens), 0).label("total_tokens"),
                func.coalesce(func.sum(ModelUsageLog.cost_input), 0.0).label("cost_input"),
                func.coalesce(func.sum(ModelUsageLog.cost_output), 0.0).label("cost_output"),
                func.coalesce(func.sum(ModelUsageLog.cost_total), 0.0).label("cost_total"),
            )
            result = await session.execute(stmt)
            row = result.one()
            data = row._mapping
            return {
                "usage_records": int(data.get("usage_records", 0) or 0),
                "sessions": int(data.get("sessions", 0) or 0),
                "input_tokens": int(data.get("input_tokens", 0) or 0),
                "output_tokens": int(data.get("output_tokens", 0) or 0),
                "total_tokens": int(data.get("total_tokens", 0) or 0),
                "cost_input": float(data.get("cost_input", 0.0) or 0.0),
                "cost_output": float(data.get("cost_output", 0.0) or 0.0),
                "cost_total": float(data.get("cost_total", 0.0) or 0.0),
            }

    async def aggregate_by_session(self) -> List[Dict[str, object]]:
        async with self.db_provider.get_session() as session:
            stmt = (
                select(
                    ModelUsageLog.session_id.label("session_id"),
                    func.count(ModelUsageLog.id).label("usage_records"),
                    func.coalesce(func.sum(ModelUsageLog.input_tokens), 0).label("input_tokens"),
                    func.coalesce(func.sum(ModelUsageLog.output_tokens), 0).label("output_tokens"),
                    func.coalesce(func.sum(ModelUsageLog.total_tokens), 0).label("total_tokens"),
                    func.coalesce(func.sum(ModelUsageLog.cost_input), 0.0).label("cost_input"),
                    func.coalesce(func.sum(ModelUsageLog.cost_output), 0.0).label("cost_output"),
                    func.coalesce(func.sum(ModelUsageLog.cost_total), 0.0).label("cost_total"),
                )
                .group_by(ModelUsageLog.session_id)
            )
            result = await session.execute(stmt)
            rows = []
            for row in result.all():
                data = row._mapping
                rows.append(
                    {
                        "session_id": data.get("session_id"),
                        "usage_records": int(data.get("usage_records", 0) or 0),
                        "input_tokens": int(data.get("input_tokens", 0) or 0),
                        "output_tokens": int(data.get("output_tokens", 0) or 0),
                        "total_tokens": int(data.get("total_tokens", 0) or 0),
                        "cost_input": float(data.get("cost_input", 0.0) or 0.0),
                        "cost_output": float(data.get("cost_output", 0.0) or 0.0),
                        "cost_total": float(data.get("cost_total", 0.0) or 0.0),
                    }
                )
            return rows

