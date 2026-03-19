"""Agents endpoint for listing available agent prompts."""

from fastapi import APIRouter, HTTPException, Query, Query, status
from langfuse import get_client, observe, propagate_attributes

from app.api.v1.services import get_orchestration_agent
from app.core.langfuse_client import langfuse

router = APIRouter()

langfuse = get_client()

@router.get("", response_model=dict[str, str])
@observe(name="list_agents")
async def list_agents(
    session_id: str | None = Query(None, alias="sessionId"),
) -> dict[str, str]:
    """Return available agents mapped to their current system prompts."""


    with langfuse.trace(
        name="list_agents",
        metadata={
            "endpoint": "/api/v1/agents",
            "method": "GET",
        },
    ) as trace:
        try:
            orchestrator = get_orchestration_agent()
        except Exception as exc:
            trace.update(output={"error": "orchestrator_unavailable", "reason": str(exc)})
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

        langfuse.update_current_span(
            output={"success": True, "agent_count": len(result)}
        )
        return result