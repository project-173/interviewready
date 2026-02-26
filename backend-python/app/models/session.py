"""Session management models."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from .agent import AgentResponse


class SessionContext(BaseModel):
    """Session context for managing conversation state."""
    
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    shared_memory: Optional[Dict[str, Any]] = Field(default_factory=dict)
    history: Optional[List[AgentResponse]] = Field(default_factory=list)
    decision_trace: Optional[List[str]] = Field(default_factory=list)
    
    def add_to_history(self, response: AgentResponse) -> None:
        """Add an agent response to the session history."""
        if self.history is None:
            self.history = []
        self.history.append(response)


class SharedState(BaseModel):
    """Shared state for agent coordination."""
    
    session_id: Optional[str] = None
    current_resume: Optional[str] = None  # Resume ID or content
    current_job_description: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    analysis_results: Optional[Dict[str, Any]] = Field(default_factory=dict)
    recommendations: Optional[List[str]] = Field(default_factory=list)
    workflow_state: Optional[str] = None
    last_updated: Optional[str] = None
