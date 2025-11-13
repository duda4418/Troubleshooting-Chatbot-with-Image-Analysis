from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlmodel import select

from app.core.database import DatabaseProvider
from app.data.repositories.base_repository import BaseRepository
from app.data.schemas.models import ProblemCause


class ProblemCauseRepository(BaseRepository[ProblemCause]):
    def __init__(self, db_provider: DatabaseProvider) -> None:
        super().__init__(db_provider, ProblemCause)

    async def list_by_category(self, category_id: UUID) -> List[ProblemCause]:
        async with self.db_provider.get_session() as session:
            statement = select(ProblemCause).where(ProblemCause.category_id == category_id).order_by(ProblemCause.default_priority)
            result = await session.execute(statement)
            return list(result.scalars().all())

    async def get_by_category_and_slug(self, category_id: UUID, slug: str) -> Optional[ProblemCause]:
        async with self.db_provider.get_session() as session:
            statement = select(ProblemCause).where(
                ProblemCause.category_id == category_id,
                ProblemCause.slug == slug,
            )
            result = await session.execute(statement)
            return result.scalar_one_or_none()
