from __future__ import annotations

import logging
from typing import List
from uuid import UUID

from app.data.DTO.assistant_api_dto import ConversationMessageRead, ConversationSessionRead
from app.data.repositories import (
    ConversationMessageRepository,
    ConversationSessionRepository,
)

logger = logging.getLogger(__name__)


class SessionManagerService:
    """Manages session listing, history, and feedback."""
    
    def __init__(
        self,
        *,
        session_repo: ConversationSessionRepository,
        message_repo: ConversationMessageRepository,
    ):
        self._session_repo = session_repo
        self._message_repo = message_repo
    
    async def list_sessions(self, limit: int = 50) -> List[ConversationSessionRead]:
        """List recent conversation sessions."""
        sessions = await self._session_repo.list_recent(limit=limit)
        return [
            ConversationSessionRead(
                id=s.id,
                status=s.status,
                created_at=s.created_at,
                updated_at=s.updated_at,
                ended_at=s.ended_at,
                feedback_rating=s.feedback_rating,
            )
            for s in sessions
        ]
    
    async def get_session_history(
        self, session_id: UUID, limit: int = 100
    ) -> tuple[ConversationSessionRead, List[ConversationMessageRead]]:
        """Get session and its message history."""
        session = await self._session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        messages = await self._message_repo.list_by_session(session_id, limit=limit)
        
        session_read = ConversationSessionRead(
            id=session.id,
            status=session.status,
            created_at=session.created_at,
            updated_at=session.updated_at,
            ended_at=session.ended_at,
            feedback_rating=session.feedback_rating,
        )
        
        # Return all messages including client_hidden ones
        # Frontend needs them to merge form submissions into forms
        messages_read = [
            ConversationMessageRead(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                message_metadata=m.message_metadata or {},
                created_at=m.created_at,
                helpful=m.helpful,
            )
            for m in messages
        ]
        
        return session_read, messages_read
    
    async def submit_feedback(
        self, session_id: UUID, rating: int, comment: str | None = None
    ) -> None:
        """Submit feedback for a session."""
        session = await self._session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Allow feedback for resolved or escalated sessions, but not closed ones
        if session.status == "closed":
            raise PermissionError("Cannot submit feedback for a closed session")
        
        # Update feedback fields without changing the session status
        session.feedback_rating = rating
        session.feedback_text = comment
        # Don't change status - keep it as "resolved" or "escalated"
        
        await self._session_repo.update(session)
        logger.info(f"Feedback submitted for session {session_id}: rating={rating}, status remains={session.status}")
