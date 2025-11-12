from __future__ import annotations

from typing import Iterable, List
from uuid import UUID

from sqlmodel import select  # type: ignore[import-untyped]

from app.core.database import DatabaseProvider
from app.data.repositories.base_repository import BaseRepository
from app.data.schemas.models import ProblemSolution


class ProblemSolutionRepository(BaseRepository[ProblemSolution]):
    def __init__(self, db_provider: DatabaseProvider) -> None:
        super().__init__(db_provider, ProblemSolution)

    async def list_by_cause(self, cause_id: UUID, *, limit: int = 10) -> List[ProblemSolution]:
        async with self.db_provider.get_session() as session:
            statement = (
                select(ProblemSolution)
                .where(ProblemSolution.cause_id == cause_id)
                .order_by(ProblemSolution.step_order, ProblemSolution.title)
                .limit(limit)
            )
            result = await session.execute(statement)
            return list(result.scalars().all())

    async def list_by_ids(self, solution_ids: Iterable[UUID]) -> List[ProblemSolution]:
        ids = list(solution_ids)
        if not ids:
            return []
        async with self.db_provider.get_session() as session:
            statement = select(ProblemSolution).where(ProblemSolution.id.in_(ids))  # type: ignore[arg-type]
            result = await session.execute(statement)
            return list(result.scalars().all())
    
    async def get_by_slug(self, slug: str) -> ProblemSolution | None:
        """Get a solution by its slug."""
        async with self.db_provider.get_session() as session:
            statement = select(ProblemSolution).where(ProblemSolution.slug == slug)
            result = await session.execute(statement)
            return result.scalar_one_or_none()
