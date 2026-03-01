import os
import json
import time
from typing import Any, Optional, Dict
from datetime import datetime


class OrchestrationLogger:
    """Structured logger for orchestration visibility."""
    
    def __init__(self, service_name: str = "interviewready"):
        self.service_name = service_name
        self.log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
        
    def _should_log(self, level: str) -> bool:
        """Check if we should log at this level."""
        levels = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
        return levels.get(level, 0) >= levels.get(self.log_level, 0)
    
    def _format_message(self, level: str, message: str, **kwargs) -> str:
        """Format a structured log message."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": self.service_name,
            "level": level,
            "message": message,
            **kwargs
        }
        return json.dumps(log_entry, default=str)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        if self._should_log("DEBUG"):
            formatted = self._format_message("DEBUG", message, **kwargs)
            print(f"    \033[2m{formatted}\033[0m")
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        if self._should_log("INFO"):
            formatted = self._format_message("INFO", message, **kwargs)
            print(formatted)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        if self._should_log("WARNING"):
            formatted = self._format_message("WARNING", message, **kwargs)
            print(f"\033[33m{formatted}\033[0m")
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        if self._should_log("ERROR"):
            formatted = self._format_message("ERROR", message, **kwargs)
            print(f"\033[31m{formatted}\033[0m")
    
    def log_orchestration_start(self, input_text: str, session_id: str, user_id: Optional[str] = None) -> None:
        """Log orchestration request start."""
        self.info(
            "Orchestration request started",
            event="orchestration_start",
            session_id=session_id,
            user_id=user_id,
            input_length=len(input_text),
            input_preview=input_text[:100] + "..." if len(input_text) > 100 else input_text
        )
    
    def log_intent_analysis(self, input_text: str, intent_result: list[str], analysis_method: str, session_id: str) -> None:
        """Log intent analysis results."""
        self.info(
            "Intent analysis completed",
            event="intent_analysis",
            session_id=session_id,
            analysis_method=analysis_method,
            selected_agents=intent_result,
            input_length=len(input_text)
        )
    
    def log_agent_execution_start(self, agent_name: str, input_text: str, session_id: str, agent_index: int) -> None:
        """Log agent execution start."""
        self.info(
            f"Agent execution started: {agent_name}",
            event="agent_execution_start",
            session_id=session_id,
            agent_name=agent_name,
            agent_index=agent_index,
            input_length=len(input_text),
            input_preview=input_text[:100] + "..." if len(input_text) > 100 else input_text
        )
    
    def log_agent_execution_complete(self, agent_name: str, response: Any, session_id: str, execution_time: float) -> None:
        """Log agent execution completion."""
        response_content = getattr(response, 'content', str(response))
        confidence_score = getattr(response, 'confidence_score', None)
        
        self.info(
            f"Agent execution completed: {agent_name}",
            event="agent_execution_complete",
            session_id=session_id,
            agent_name=agent_name,
            execution_time_ms=round(execution_time * 1000, 2),
            response_length=len(response_content) if response_content else 0,
            confidence_score=confidence_score,
            response_preview=response_content[:100] + "..." if response_content and len(response_content) > 100 else response_content
        )
    
    def log_agent_error(self, agent_name: str, error: Exception, session_id: str) -> None:
        """Log agent execution error."""
        self.error(
            f"Agent execution failed: {agent_name}",
            event="agent_execution_error",
            session_id=session_id,
            agent_name=agent_name,
            error_type=type(error).__name__,
            error_message=str(error)
        )
    
    def log_orchestration_complete(self, session_id: str, total_time: float, agent_sequence: list[str]) -> None:
        """Log orchestration completion."""
        self.info(
            "Orchestration request completed",
            event="orchestration_complete",
            session_id=session_id,
            total_time_ms=round(total_time * 1000, 2),
            agents_executed=agent_sequence,
            agent_count=len(agent_sequence)
        )
    
    def log_state_transition(self, from_state: str, to_state: str, session_id: str, **kwargs) -> None:
        """Log state transition."""
        self.debug(
            f"State transition: {from_state} -> {to_state}",
            event="state_transition",
            session_id=session_id,
            from_state=from_state,
            to_state=to_state,
            **kwargs
        )
    
    def log_api_call(self, service: str, operation: str, session_id: str, **kwargs) -> None:
        """Log external API call."""
        self.debug(
            f"API call: {service}.{operation}",
            event="api_call",
            session_id=session_id,
            service=service,
            operation=operation,
            **kwargs
        )


# Global logger instance
logger = OrchestrationLogger()


# Legacy debug function for backward compatibility
def debug(message: str, prefix: str = "DEBUG") -> None:
    """Legacy debug function for backward compatibility."""
    logger.debug(message, legacy_prefix=prefix)
