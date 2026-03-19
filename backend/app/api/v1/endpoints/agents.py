"""Agents endpoint for listing available agent prompts."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.services import get_orchestration_agent
from app.core.auth import get_current_user
from app.core.langfuse_client import langfuse
from fastapi import APIRouter, HTTPException, Query, status
from langfuse import get_client, observe, propagate_attributes

from app.api.v1.services import get_orchestration_agent

router = APIRouter()

langfuse = get_client()

@router.get("", response_model=dict[str, str])
@observe(name="list_agents")
async def list_agents(
    session_id: str | None = Query(None, alias="sessionId"),
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: ARG001
) -> dict[str, str]:
    """Return available agents mapped to their current system prompts."""

    user_id = str(
        current_user.get("uid")
        or current_user.get("user_id")
        or current_user.get("sub")
        or ""
    )

    with langfuse.trace(
        name="list_agents",
        session_id=session_id or user_id,
        user_id=user_id,
        metadata={
            "endpoint": "/api/v1/agents",
            "method": "GET",
        },
    ) as trace:
        try:
            orchestrator = get_orchestration_agent()
        except Exception as exc:
            trace.update(session_id=session_id, output={"error": "orchestrator_unavailable", "reason": str(exc)})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Orchestration service unavailable: {exc}",
            ) from exc

        result = {
            name: agent.get_system_prompt()
            for name, agent in orchestrator.get_agents().items()
        }

        trace.update(session_id=session_id, output={"success": True, "agent_count": len(result)})
        return result
