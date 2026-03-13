"""Agents endpoint for listing available agent prompts."""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.api.v1.services import get_orchestration_agent

router = APIRouter()


@router.get("", response_model=dict[str, str])
async def list_agents() -> dict[str, str]:
    """Return available agents mapped to their current system prompts."""
    try:
        orchestrator = get_orchestration_agent()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Orchestration service unavailable: {exc}",
        ) from exc

    return {
        name: agent.get_system_prompt()
        for name, agent in orchestrator.get_agents().items()
    }
