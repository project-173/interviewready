"""Base agent classes and protocols."""

from abc import ABC, abstractmethod
from typing import Protocol, Optional, Dict, Any, List
from ..models.agent import AgentResponse
from ..models.session import SessionContext


class BaseAgentProtocol(Protocol):
    """Protocol defining the interface for all agents."""
    
    def get_name(self) -> str:
        """Get the agent name."""
        ...
    
    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        """Process input and return agent response."""
        ...
    
    def update_system_prompt(self, new_prompt: str) -> None:
        """Update the system prompt."""
        ...
    
    def get_system_prompt(self) -> str:
        """Get the current system prompt."""
        ...


class BaseAgent(ABC, BaseAgentProtocol):
    """Abstract base agent implementation."""
    
    def __init__(self, gemini_service: 'GeminiService', system_prompt: str, name: str):
        """Initialize the base agent.
        
        Args:
            gemini_service: Service for Gemini API interactions
            system_prompt: Initial system prompt for the agent
            name: Agent name
        """
        self.gemini_service = gemini_service
        self.system_prompt = system_prompt
        self.name = name
    
    def get_name(self) -> str:
        """Get the agent name."""
        return self.name
    
    def update_system_prompt(self, new_prompt: str) -> None:
        """Update the system prompt."""
        self.system_prompt = new_prompt
    
    def get_system_prompt(self) -> str:
        """Get the current system prompt."""
        return self.system_prompt
    
    @abstractmethod
    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        """Process input and return agent response. Must be implemented by subclasses."""
        pass
    
    def call_gemini(self, input_text: str, context: SessionContext) -> str:
        """Call Gemini API with system prompt and user input.
        
        Args:
            input_text: User input text
            context: Session context for additional information
            
        Returns:
            Gemini response text
        """
        return self.gemini_service.generate_response(
            system_prompt=self.system_prompt,
            user_input=input_text,
            context=context
        )
