from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func
from sqlmodel import select

from app.core.database import DatabaseProvider
from app.data.repositories.base_repository import BaseRepository
from app.data.schemas.models import ConversationSession, utcnow
from app.data.repositories.conversation_image_repository import ConversationImageRepository
from app.data.repositories.conversation_message_repository import ConversationMessageRepository


class ConversationSessionRepository(BaseRepository[ConversationSession]):
    """Data access for conversation sessions."""

    def __init__(self, db_provider: DatabaseProvider):
        super().__init__(db_provider, ConversationSession)

    async def get_with_messages(self, session_id: UUID) -> Optional[ConversationSession]:
        return await self.get_by_id(session_id)

    async def touch(self, session_id: UUID) -> Optional[ConversationSession]:
        async with self.db_provider.get_session() as session:
            existing = await session.get(ConversationSession, session_id)
            if not existing:
                return None
            existing.updated_at = utcnow()
            session.add(existing)
            await session.commit()
            await session.refresh(existing)
            return existing

    async def set_status(self, session_id: UUID, status: str) -> Optional[ConversationSession]:
        async with self.db_provider.get_session() as session:
            existing = await session.get(ConversationSession, session_id)
            if not existing:
                return None
            existing.status = status
            existing.updated_at = utcnow()
            session.add(existing)
            await session.commit()
            await session.refresh(existing)
            return existing

    async def close(self, session_id: UUID, *, status: str) -> Optional[ConversationSession]:
        async with self.db_provider.get_session() as session:
            existing = await session.get(ConversationSession, session_id)
            if not existing:
                return None
            now = utcnow()
            existing.status = status
            existing.updated_at = now
            existing.ended_at = now
            session.add(existing)
            await session.commit()
            await session.refresh(existing)
            return existing

    async def set_feedback(
        self,
        session_id: UUID,
        *,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> Optional[ConversationSession]:
        async with self.db_provider.get_session() as session:
            existing = await session.get(ConversationSession, session_id)
            if not existing:
                return None
            existing.feedback_rating = rating
            existing.feedback_text = comment
            existing.updated_at = utcnow()
            session.add(existing)
            await session.commit()
            await session.refresh(existing)
            return existing

    async def list_recent(self, *, limit: int = 50) -> list[ConversationSession]:
        async with self.db_provider.get_session() as session:
            stmt = (
                select(ConversationSession)
                .order_by(ConversationSession.updated_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_many(self, session_ids: Sequence[UUID]) -> list[ConversationSession]:
        if not session_ids:
            return []
        async with self.db_provider.get_session() as session:
            stmt = (
                select(ConversationSession)
                .where(ConversationSession.id.in_(session_ids))
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_feedback_stats(self) -> tuple[Optional[float], int]:
        async with self.db_provider.get_session() as session:
            stmt = select(
                func.avg(ConversationSession.feedback_rating),
                func.count(ConversationSession.feedback_rating),
            ).where(ConversationSession.feedback_rating.is_not(None))
            result = await session.execute(stmt)
            try:
                average, count = result.one()
            except Exception:
                return None, 0
            if count is None or count == 0:
                return None, 0
            return (float(average) if average is not None else None, int(count))

    async def get_context(self, session_id: UUID) -> Optional[dict]:
        """Return conversation context including messages and image analysis descriptions.

        Structure:
        {
            'session': ConversationSession,
            'messages': [ConversationMessage, ...],
            'image_descriptions': [str, ...],
        }

        Only retrieves already generated analysis_text to avoid reprocessing images.
        """
        # Fetch session
        session_obj = await self.get_by_id(session_id)
        if not session_obj:
            return None

        # Fetch messages (re-using ConversationMessageRepository for consistency)
        message_repo = ConversationMessageRepository(self.db_provider)
        messages = await message_repo.list_by_session(session_id=session_id, limit=500)

        # Fetch image descriptions (use image repo helper)
        image_repo = ConversationImageRepository(self.db_provider)
        image_descriptions = await image_repo.get_analysis_context(session_id=session_id)

        return {
            'session': session_obj,
            'messages': messages,
            'image_descriptions': image_descriptions,
        }
