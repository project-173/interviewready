"""Session endpoints for retrieving persisted session state."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.v1.services import get_session_context
from app.core.auth import get_current_user
from app.models.resume import Resume

router = APIRouter()


@router.get("/{session_id}/resume")
async def get_session_resume(
    session_id: Annotated[str, Path()],
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> Resume:
    """Return parsed resume JSON currently persisted for a session."""
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