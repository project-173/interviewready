"""Agents endpoint for listing available agent prompts."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.api.v1.services import get_orchestration_agent
from app.core.langfuse_client import langfuse

router = APIRouter()


@router.get("", response_model=dict[str, str])
async def list_agents() -> dict[str, str]:
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
