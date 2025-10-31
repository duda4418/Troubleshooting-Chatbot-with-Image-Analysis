from typing import Optional
from uuid import UUID

from sqlmodel import select

from app.core.database import DatabaseProvider
from app.data.repositories.base_repository import BaseRepository
from app.data.schemas.models import ConversationSession, ConversationMessage, utcnow
from app.data.schemas.models import ConversationImage
from app.data.repositories.conversation_image_repository import ConversationImageRepository
from app.data.repositories.conversation_form_repository import ConversationFormRepository
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

    async def list_recent(self, *, limit: int = 50) -> list[ConversationSession]:
        async with self.db_provider.get_session() as session:
            stmt = (
                select(ConversationSession)
                .order_by(ConversationSession.updated_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_context(self, session_id: UUID) -> Optional[dict]:
        """Return full conversation context including messages, forms, and image analysis descriptions.

        Structure:
        {
            'session': ConversationSession,
            'messages': [ConversationMessage, ...],
            'image_descriptions': [str, ...],
            'forms': [
                {
                    'form_id': str,
                    'title': str,
                    'status': str,
                    'rejection_reason': Optional[str],
                    'updated_at': Optional[str],
                    'inputs': [{'question': str, 'type': str, 'answer': str}, ...]
                },
                ...
            ]
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

        # Fetch simplified form context for AI consumption
        form_repo = ConversationFormRepository(self.db_provider)
        forms = await form_repo.get_form_context(session_id=session_id)

        return {
            'session': session_obj,
            'messages': messages,
            'image_descriptions': image_descriptions,
            'forms': forms,
        }
