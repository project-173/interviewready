"""Session endpoints for retrieving persisted session state."""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Path, status, Request

from app.api.v1.services import get_session_context
from app.core.limiter import limiter
from app.core.config import settings
from app.models.resume import Resume

router = APIRouter()


@router.get("/{session_id}/resume")
@limiter.limit("50/minute")
async def get_session_resume(
    request: Request,
    session_id: Annotated[str, Path()],
) -> Resume:
    """Return parsed resume JSON currently persisted for a session."""
    user_id = "dev-user"

    try:
        context = get_session_context(session_id=session_id, user_id=user_id)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    if context is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    shared_memory = context.shared_memory or {}
    raw_resume = shared_memory.get("current_resume")
    if not isinstance(raw_resume, dict) or not raw_resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No parsed resume found for this session",
        )

    try:
        return Resume.model_validate(raw_resume)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stored resume data is invalid: {exc}",
        ) from exc