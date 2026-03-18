"""Agents endpoint for listing available agent prompts."""

from fastapi import APIRouter, HTTPException, Query, status
from langfuse import get_client, observe, propagate_attributes

from app.api.v1.services import get_orchestration_agent

router = APIRouter()

langfuse = get_client()

@router.get("", response_model=dict[str, str])
@observe(name="list_agents")
async def list_agents(
    session_id: str | None = Query(None, alias="sessionId"),
) -> dict[str, str]:
    """Return available agents mapped to their current system prompts."""

    with propagate_attributes(session_id=session_id or ""):
        langfuse.update_current_span(
            metadata={
                "endpoint": "/api/v1/agents",
                "method": "GET",
            }
        )

        try:
            orchestrator = get_orchestration_agent()
        except Exception as exc:
            langfuse.update_current_span(
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

        langfuse.update_current_span(
            output={"success": True, "agent_count": len(result)}
        )
        return result