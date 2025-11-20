from typing import List
from uuid import UUID

from sqlmodel import select

from app.core.database import DatabaseProvider
from app.data.repositories.base_repository import BaseRepository
from app.data.schemas.models import ConversationImage


class ConversationImageRepository(BaseRepository[ConversationImage]):
    """Data access for conversation images with AI analysis."""

    def __init__(self, db_provider: DatabaseProvider):
        super().__init__(db_provider, ConversationImage)

    async def list_by_session(self, session_id: UUID, limit: int = 100) -> List[ConversationImage]:
        async with self.db_provider.get_session() as session:
            stmt = (
                select(ConversationImage)
                .where(ConversationImage.session_id == session_id)
                .order_by(ConversationImage.created_at)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_message(self, message_id: UUID) -> List[ConversationImage]:
        async with self.db_provider.get_session() as session:
            stmt = (
                select(ConversationImage)
                .where(ConversationImage.message_id == message_id)
                .order_by(ConversationImage.created_at)
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_analysis_context(self, session_id: UUID) -> List[str]:
        """Return a list of analysis_text strings for images in a session (non-empty only)."""
        images = await self.list_by_session(session_id=session_id, limit=500)
        seen: set[str] = set()
        descriptions: List[str] = []
        for img in images:
            if not img.analysis_text:
                continue
            text = img.analysis_text.strip()
            if not text:
                continue
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            details = []
            metadata = img.analysis_metadata or {}
            raw_details = metadata.get("details") if isinstance(metadata, dict) else None
            if isinstance(raw_details, list):
                details = [str(item).strip() for item in raw_details if str(item).strip()]
            elif isinstance(raw_details, str) and raw_details.strip():
                details = [raw_details.strip()]

            if details:
                detail_text = "; ".join(details[:4])
                descriptions.append(f"{text} (Image details: {detail_text})")
            else:
                descriptions.append(text)
        return descriptions
