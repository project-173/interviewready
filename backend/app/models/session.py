"""Session management models."""

from typing import Any

from pydantic import BaseModel, Field

from .agent import AgentResponse


class SessionContext(BaseModel):
    """Session context for managing conversation state."""

    session_id: str | None = None
    user_id: str | None = None
    shared_memory: dict[str, Any] | None = Field(default_factory=dict)
    history: list[AgentResponse] | None = Field(default_factory=list)
    decision_trace: list[str] | None = Field(default_factory=list)
    resume_data: str | None = None  # Resume text content
    job_description: str | None = None  # Job description text

    def add_to_history(self, response: AgentResponse) -> None:
        """Add an agent response to the session history."""
        if self.history is None:
            self.history = []
        self.history.append(response)


class SharedState(BaseModel):
    """Shared state for agent coordination."""

    session_id: str | None = None
    current_resume: str | None = None  # Resume ID or content
    current_job_description: str | None = None
    extracted_data: dict[str, Any] | None = Field(default_factory=dict)
    analysis_results: dict[str, Any] | None = Field(default_factory=dict)
    recommendations: list[str] | None = Field(default_factory=list)
    workflow_state: str | None = None
    last_updated: str | None = None
