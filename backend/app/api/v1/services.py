"""API service dependencies for orchestration and session management."""

from __future__ import annotations

from functools import lru_cache

from app.agents import (
    AgentRegistry,
    GeminiService,
)
from app.api.v1.session_store import SessionStore
from app.governance import SharpGovernanceService
from app.models import SessionContext
from app.orchestration import OrchestrationAgent

_session_store = SessionStore()


@lru_cache(maxsize=1)
def get_orchestration_agent() -> OrchestrationAgent:
    """Build and cache the orchestration agent graph and dependencies."""
    gemini_service = GeminiService()
    governance = SharpGovernanceService()
    registry = AgentRegistry()
    agents = registry.build_agents(gemini_service)
    return OrchestrationAgent(
        agent_list=agents,
        governance=governance,
    )


def get_or_create_session_context(session_id: str, user_id: str) -> SessionContext:
    """Return existing session context or create it for this user."""
    return _session_store.get_or_create(session_id=session_id, user_id=user_id)


def get_session_context(session_id: str, user_id: str) -> SessionContext | None:
    """Return existing session context for this user, if present."""
    return _session_store.get(session_id=session_id, user_id=user_id)
