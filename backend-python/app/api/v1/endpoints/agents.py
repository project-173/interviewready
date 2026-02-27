"""Agents endpoint for listing available agent prompts."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.services import get_orchestration_agent
from app.core.auth import get_current_user

router = APIRouter()


@router.get("", response_model=dict[str, str])
async def list_agents(
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: ARG001
) -> dict[str, str]:
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
