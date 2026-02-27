"""API service dependencies for orchestration and session management."""

from __future__ import annotations

from functools import lru_cache
from threading import RLock

from app.agents import (
    ContentStrengthAgent,
    GeminiService,
    InterviewCoachAgent,
    JobAlignmentAgent,
    ResumeCriticAgent,
)
from app.governance import SharpGovernanceService
from app.models import SessionContext
from app.orchestration import OrchestrationAgent

_sessions: dict[str, SessionContext] = {}
_sessions_lock = RLock()


@lru_cache(maxsize=1)
def get_orchestration_agent() -> OrchestrationAgent:
    """Build and cache the orchestration agent graph and dependencies."""
    gemini_service = GeminiService()
    governance = SharpGovernanceService()
    agents = [
        ResumeCriticAgent(gemini_service),
        ContentStrengthAgent(gemini_service),
        JobAlignmentAgent(gemini_service),
        InterviewCoachAgent(gemini_service),
    ]
    return OrchestrationAgent(
        agent_list=agents,
        governance=governance,
        intent_gemini_service=gemini_service,
    )


def get_or_create_session_context(session_id: str, user_id: str) -> SessionContext:
    """Return existing session context or create it for this user."""
    with _sessions_lock:
        context = _sessions.get(session_id)
        if context is None:
            context = SessionContext(session_id=session_id, user_id=user_id)
            _sessions[session_id] = context
            return context

        if context.user_id != user_id:
            error_message = "Unauthorized access to session"
            raise PermissionError(error_message)

        return context
