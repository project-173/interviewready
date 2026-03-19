"""Agents endpoint for listing available agent prompts."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.services import get_orchestration_agent
from app.core.auth import get_current_user
from langfuse import Langfuse, observe, propagate_attributes

langfuse = Langfuse()

router = APIRouter()

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

    effective_session_id = session_id or user_id

    with langfuse.start_as_current_observation(
        as_type="span",
        name="list_agents",
        metadata={
            "endpoint": "/api/v1/agents",
            "method": "GET",
        },
    ) as trace:
        with propagate_attributes(user_id=user_id, session_id=effective_session_id):
            try:
                orchestrator = get_orchestration_agent()
            except Exception as exc:
                trace.update(
                    output={"error": "orchestrator_unavailable", "reason": str(exc)}
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Orchestration service unavailable: {exc}",
                ) from exc

            result = {
                name: agent.get_system_prompt()
                for name, agent in orchestrator.get_agents().items()
            }

            trace.update(output={"success": True, "agent_count": len(result)})
            return result
