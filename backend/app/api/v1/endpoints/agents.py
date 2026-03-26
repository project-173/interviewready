"""Agents endpoint for listing available agent prompts."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from langfuse import Langfuse, observe, propagate_attributes
from app.core.limiter import limiter

from app.api.v1.services import get_orchestration_agent

langfuse = Langfuse()

router = APIRouter()

SessionId = Annotated[str | None, Query(alias="sessionId")]
OrchestrationAgent = Annotated[object, Depends(get_orchestration_agent)]

@router.get("")
@limiter.limit("20/minute")
@observe(name="list_agents")
async def list_agents(
    request: Request,
    orchestrator: OrchestrationAgent,
    session_id: SessionId = None,
) -> dict[str, str]:
    """Return available agents mapped to their current system prompts."""

    user_id = "user-id"
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
            if orchestrator is None:
                trace.update(
                    output={"error": "orchestrator_unavailable"}
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Orchestration service unavailable",
                )

        result = {
            name: agent.get_system_prompt()
            for name, agent in orchestrator.get_agents().items()
        }

        langfuse.update_current_span(
            output={"success": True, "agent_count": len(result)}
        )
        return result