"""Chat endpoint for interacting with the agentic system."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool

from app.api.v1.services import (
    get_or_create_session_context,
    get_orchestration_agent,
)
from app.core.auth import get_current_user
from app.models import AgentResponse, ChatRequest

router = APIRouter()


@router.post("", response_model=AgentResponse)
async def chat_endpoint(
    request: ChatRequest,
    session_id: str = Query(..., alias="sessionId"),
    current_user: dict = Depends(get_current_user),
) -> AgentResponse:
    """Run orchestration for the chat message within a user-owned session."""
    user_id = str(
        current_user.get("uid")
        or current_user.get("user_id")
        or current_user.get("sub")
        or ""
    )
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing user identity in authentication token",
        )

    try:
        context = get_or_create_session_context(session_id=session_id, user_id=user_id)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    try:
        orchestrator = get_orchestration_agent()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Orchestration service unavailable: {exc}",
        ) from exc

    try:
        return await run_in_threadpool(orchestrator.orchestrate, request, context)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat request: {exc}",
        ) from exc
