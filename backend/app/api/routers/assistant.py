from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.core.dependencies import get_assistant_service
from app.data.DTO import (
    AssistantMessageRequest,
    AssistantMessageResponse,
    ConversationHistoryResponse,
    ConversationSessionRead,
    SessionFeedbackRequest,
)
from app.services.assistant_service import AssistantService

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/messages", response_model=AssistantMessageResponse)
async def send_message(
    payload: AssistantMessageRequest,
    assistant_service: AssistantService = Depends(get_assistant_service),
) -> AssistantMessageResponse:
    try:
        return await assistant_service.handle_message(payload)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/sessions", response_model=List[ConversationSessionRead])
async def list_sessions(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of sessions to return"),
    assistant_service: AssistantService = Depends(get_assistant_service),
) -> List[ConversationSessionRead]:
    return await assistant_service.list_sessions(limit=limit)


@router.get(
    "/sessions/{session_id}/history",
    response_model=ConversationHistoryResponse,
)
async def get_history(
    session_id: UUID,
    limit: int = Query(100, ge=1, le=200, description="Maximum number of messages to return"),
    assistant_service: AssistantService = Depends(get_assistant_service),
) -> ConversationHistoryResponse:
    try:
        session, messages = await assistant_service.get_session_history(session_id, limit)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="Session not found") from exc

    return ConversationHistoryResponse(session=session, history=messages)


@router.post(
    "/sessions/{session_id}/feedback",
    status_code=204,
)
async def submit_feedback(
    session_id: UUID,
    payload: SessionFeedbackRequest,
    assistant_service: AssistantService = Depends(get_assistant_service),
) -> Response:
    try:
        await assistant_service.submit_feedback(session_id, rating=payload.rating, comment=payload.comment)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="Session not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(status_code=204)
