"""Session endpoints for retrieving persisted session state."""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Path, status

from app.api.v1.services import get_session_context
from app.core.langfuse_client import langfuse, propagate_attributes
from app.models.resume import Resume

router = APIRouter()


@router.get("/{session_id}/resume")
async def get_session_resume(
    session_id: Annotated[str, Path()],
) -> Resume:
    """Return parsed resume JSON currently persisted for a session."""
    user_id = "dev-user"

    with langfuse.trace(
        name="get_session_resume",
        session_id=session_id,
        metadata={
            "endpoint": "/api/v1/sessions/{session_id}/resume",
            "method": "GET",
        },
    ) as trace:
        with propagate_attributes(user_id=user_id, session_id=session_id):
            with trace.span(name="load_session") as span:
                try:
                    context = get_session_context(session_id=session_id, user_id=user_id)
                    span.update(output={"status": "success", "session_found": context is not None})
                except PermissionError as exc:
                    span.update(output={"status": "error", "error": "permission_denied", "reason": str(exc)})
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=str(exc),
                    ) from exc

            if context is None:
                trace.update(output={"status": "error", "error": "session_not_found"})
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found",
                )

            with trace.span(name="extract_resume") as span:
                shared_memory = context.shared_memory or {}
                raw_resume = shared_memory.get("current_resume")
                if not isinstance(raw_resume, dict) or not raw_resume:
                    span.update(output={"status": "error", "error": "resume_not_found"})
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="No parsed resume found for this session",
                    )

                try:
                    resume = Resume.model_validate(raw_resume)
                    span.update(output={"status": "success"})
                except Exception as exc:
                    span.update(output={"status": "error", "error": "invalid_resume", "reason": str(exc)})
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Stored resume data is invalid: {exc}",
                    ) from exc

            trace.update(output={"status": "success"})
            return resume