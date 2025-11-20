from __future__ import annotations

from typing import Iterable, List, Optional
from uuid import UUID

from sqlmodel import select  # type: ignore[import-untyped]

from app.core.database import DatabaseProvider
from app.data.repositories.base_repository import BaseRepository
from app.data.schemas.models import SessionSuggestion, SuggestionStatus


class SessionSuggestionRepository(BaseRepository[SessionSuggestion]):
    def __init__(self, db_provider: DatabaseProvider) -> None:
        super().__init__(db_provider, SessionSuggestion)

    async def list_by_session(self, session_id: UUID) -> List[SessionSuggestion]:
        async with self.db_provider.get_session() as session:
            statement = select(SessionSuggestion).where(SessionSuggestion.session_id == session_id)
            result = await session.execute(statement)
            return list(result.scalars().all())

    async def list_by_solution_ids(self, session_id: UUID, solution_ids: Iterable[UUID]) -> List[SessionSuggestion]:
        ids = list(solution_ids)
        if not ids:
            return []
        async with self.db_provider.get_session() as session:
            statement = select(SessionSuggestion).where(
                SessionSuggestion.session_id == session_id,
                SessionSuggestion.solution_id.in_(ids),  # type: ignore[arg-type]
            )
            result = await session.execute(statement)
            return list(result.scalars().all())

    async def mark_completed(
        self,
        suggestion_id: UUID,
        *,
        notes: Optional[str] = None,
        status: SuggestionStatus = SuggestionStatus.COMPLETED,
    ) -> SessionSuggestion:
        async with self.db_provider.get_session() as session:
            instance = await session.get(SessionSuggestion, suggestion_id)
            if not instance:
                raise ValueError("Suggestion not found")
            instance.status = status
            instance.notes = notes
            await session.commit()
            await session.refresh(instance)
            return instance
