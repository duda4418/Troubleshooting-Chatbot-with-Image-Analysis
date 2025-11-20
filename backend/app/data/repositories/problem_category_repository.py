from __future__ import annotations

from typing import List, Optional

from sqlmodel import select

from app.core.database import DatabaseProvider
from app.data.repositories.base_repository import BaseRepository
from app.data.schemas.models import ProblemCategory


class ProblemCategoryRepository(BaseRepository[ProblemCategory]):
    def __init__(self, db_provider: DatabaseProvider) -> None:
        super().__init__(db_provider, ProblemCategory)

    async def list_all(self) -> List[ProblemCategory]:
        return await super().get_all(limit=500)

    async def get_by_slug(self, slug: str) -> Optional[ProblemCategory]:
        async with self.db_provider.get_session() as session:
            statement = select(ProblemCategory).where(ProblemCategory.slug == slug)
            result = await session.execute(statement)
            return result.scalar_one_or_none()
