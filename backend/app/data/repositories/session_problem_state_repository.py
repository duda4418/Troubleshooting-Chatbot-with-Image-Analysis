from __future__ import annotations

from typing import Optional
from uuid import UUID

from app.core.database import DatabaseProvider
from app.data.schemas.models import SessionProblemState, utcnow


class SessionProblemStateRepository:
    """Persistence helper for session-level problem classification state."""

    def __init__(self, db_provider: DatabaseProvider) -> None:
        self._db_provider = db_provider

    async def get_by_session_id(self, session_id: UUID) -> Optional[SessionProblemState]:
        async with self._db_provider.get_session() as session:
            return await session.get(SessionProblemState, session_id)

    async def upsert(
        self,
        session_id: UUID,
        *,
        category_id: Optional[UUID] = None,
        cause_id: Optional[UUID] = None,
        classification_confidence: Optional[float] = None,
        classification_source: Optional[str] = None,
        manual_override: bool = False,
    ) -> SessionProblemState:
        async with self._db_provider.get_session() as session:
            instance = await session.get(SessionProblemState, session_id)
            if instance is None:
                instance = SessionProblemState(
                    session_id=session_id,
                    category_id=category_id,
                    cause_id=cause_id,
                    classification_confidence=classification_confidence,
                    classification_source=classification_source,
                    manual_override=manual_override,
                )
                session.add(instance)
            else:
                instance.category_id = category_id
                instance.cause_id = cause_id
                instance.classification_confidence = classification_confidence
                instance.classification_source = classification_source
                instance.manual_override = manual_override
                instance.updated_at = utcnow()

            await session.commit()
            await session.refresh(instance)
            return instance
