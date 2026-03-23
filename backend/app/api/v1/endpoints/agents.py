"""Agents endpoint for listing available agent prompts."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.services import get_orchestration_agent
from app.core.langfuse_client import langfuse, propagate_attributes

router = APIRouter()

SessionId = Annotated[str | None, Query(alias="sessionId")]
OrchestrationAgent = Annotated[object, Depends(get_orchestration_agent)]

@router.get("")
async def list_agents(
    orchestrator: OrchestrationAgent,
    session_id: SessionId = None,
) -> dict[str, str]:
    """Return available agents mapped to their current system prompts."""

    user_id = "user-id"
    effective_session_id = session_id or user_id

    with langfuse.trace(
        name="list_agents",
        session_id=effective_session_id,
        metadata={
            "endpoint": "/api/v1/agents",
            "method": "GET",
        },
    ) as trace:
        with propagate_attributes(user_id=user_id, session_id=effective_session_id):
            with trace.span(name="fetch_agent_prompts") as span:
                if orchestrator is None:
                    span.update(output={"status": "error", "error": "orchestrator_unavailable"})
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Orchestration service unavailable",
                    )

                agent_map = getattr(orchestrator, "agent_list", None)
                if not isinstance(agent_map, dict):
                    span.update(output={"status": "error", "error": "agent_map_unavailable"})
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Agent registry unavailable",
                    )

                result = {
                    name: agent.get_system_prompt()
                    for name, agent in agent_map.items()
                }
                span.update(output={"status": "success", "agent_count": len(result)})

            trace.update(output={"status": "success", "agent_count": len(result)})
            return result