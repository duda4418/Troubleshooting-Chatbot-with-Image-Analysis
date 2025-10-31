from typing import List
from uuid import UUID

from sqlmodel import select

from app.core.database import DatabaseProvider
from app.data.repositories.base_repository import BaseRepository
from app.data.schemas.models import ConversationMessage, MessageRole


class ConversationMessageRepository(BaseRepository[ConversationMessage]):
    """Data access for conversation messages."""

    def __init__(self, db_provider: DatabaseProvider):
        super().__init__(db_provider, ConversationMessage)

    async def list_by_session(self, session_id: UUID, limit: int = 50) -> List[ConversationMessage]:
        async with self.db_provider.get_session() as session:
            stmt = (
                select(ConversationMessage)
                .where(ConversationMessage.session_id == session_id)
                .order_by(ConversationMessage.created_at)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_recent_by_role(
        self,
        *,
        session_id: UUID,
        role: MessageRole,
        limit: int = 5,
    ) -> List[ConversationMessage]:
        async with self.db_provider.get_session() as session:
            stmt = (
                select(ConversationMessage)
                .where(ConversationMessage.session_id == session_id)
                .where(ConversationMessage.role == role)
                .order_by(ConversationMessage.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
