"""Base agent classes and protocols."""

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol, Optional, Dict, Any
from ..core.logging import logger
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
    MOCK_RESPONSES_FILE = Path(__file__).resolve().parents[2] / "mock_responses.json"
    _mock_responses_cache: Optional[Dict[str, Any]] = None
    
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

    @classmethod
    def _load_mock_responses(cls) -> Dict[str, Any]:
        if cls._mock_responses_cache is not None:
            return cls._mock_responses_cache

        try:
            raw = cls.MOCK_RESPONSES_FILE.read_text(encoding="utf-8")
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                cls._mock_responses_cache = parsed
                return parsed
        except Exception:
            logger.warning("Failed to load mock responses file", path=str(cls.MOCK_RESPONSES_FILE))

        cls._mock_responses_cache = {}
        return cls._mock_responses_cache

    def get_mock_response_by_key(self, key: str) -> Optional[str]:
        responses = self._load_mock_responses()
        value = responses.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, (dict, list)):
            return json.dumps(value, indent=2)
        return None
    
    def call_gemini(self, input_text: str, context: SessionContext) -> str:
        """Call Gemini API with system prompt and user input.
        
        Args:
            input_text: User input text
            context: Session context for additional information
            
        Returns:
            Gemini response text
        """
        session_id = getattr(context, 'session_id', 'unknown')
        agent_name = self.get_name()
        
        # Log API call start
        logger.log_api_call("gemini", "generate_response", session_id, 
                          agent_name=agent_name, 
                          system_prompt_length=len(self.system_prompt),
                          input_length=len(input_text))
        
        api_start_time = time.time()
        
        try:
            response = self.gemini_service.generate_response(
                system_prompt=self.system_prompt,
                user_input=input_text,
                context=context
            )
            
            api_execution_time = time.time() - api_start_time
            
            # Log successful API call
            logger.debug("Gemini API call completed", 
                        session_id=session_id, 
                        agent_name=agent_name,
                        execution_time_ms=round(api_execution_time * 1000, 2),
                        response_length=len(response),
                        response_preview=response[:100] + "..." if len(response) > 100 else response)
            
            return response
            
        except Exception as e:
            api_execution_time = time.time() - api_start_time
            logger.log_agent_error(agent_name, e, session_id)
            logger.error("Gemini API call failed", 
                        session_id=session_id, 
                        agent_name=agent_name,
                        execution_time_ms=round(api_execution_time * 1000, 2),
                        error_type=type(e).__name__,
                        error_message=str(e))
            raise
