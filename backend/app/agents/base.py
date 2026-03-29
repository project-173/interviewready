"""Base agent classes and protocols."""

import json
import time
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Protocol, Optional, Dict, Any, Union, List, TypeVar, Type

from app.utils.json_parser import parse_json_object
from langfuse import Langfuse, propagate_attributes

langfuse = Langfuse()
from pydantic import BaseModel, ValidationError
from ..core.logging import logger
from ..models.agent import AgentResponse
from ..models.session import SessionContext
from ..models.agent import AgentInput
from ..utils.output_sanitizer import get_output_sanitizer
from ..security.llm_guard_scanner import get_llm_guard_scanner


class BaseAgentProtocol(Protocol):
    """Protocol defining the interface for all agents."""

    def get_name(self) -> str:
        """Get the agent name."""
        ...

    def process(
        self, input_data: AgentInput | str | bytes, context: SessionContext
    ) -> AgentResponse:
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

    def __init__(self, gemini_service: "GeminiService", system_prompt: str, name: str):
        """Initialize the base agent.

        Args:
            gemini_service: Service for Gemini API interactions
            system_prompt: Initial system prompt for the agent
            name: Agent name
        """
        self.gemini_service = gemini_service
        self.system_prompt = system_prompt
        self.name = name
        self.mock_service = None  # Initialize mock_service attribute

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
    def process(
        self, input_data: AgentInput | str | bytes, context: SessionContext
    ) -> AgentResponse:
        """Process input and return agent response. Must be implemented by subclasses."""
        pass

    @classmethod
    def _load_mock_responses(cls) -> Dict[str, Any]:
        if cls._mock_responses_cache is not None:
            return cls._mock_responses_cache

        try:
            if not cls.MOCK_RESPONSES_FILE.exists():
                logger.error(
                    f"Mock responses file does not exist at expected path: {cls.MOCK_RESPONSES_FILE}"
                )
                return {}

            raw = cls.MOCK_RESPONSES_FILE.read_text(encoding="utf-8")
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                cls._mock_responses_cache = parsed
                return parsed
        except Exception as e:
            logger.warning(
                "Failed to load mock responses file", 
                path=str(cls.MOCK_RESPONSES_FILE),
                error=str(e)
            )

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

        session_id = getattr(context, "session_id", "unknown")
        agent_name = self.get_name()

        user_id = getattr(context, "user_id", None)

        with langfuse.start_as_current_observation(
            as_type="span",
            name=f"{agent_name}_llm_call",
            metadata={"agent": agent_name, "prompt_length": len(input_text)},
        ) as trace:
            with propagate_attributes(user_id=user_id, session_id=session_id):
                with trace.start_as_current_observation(
                    as_type="span",
                    name="call_gemini",
                    input={"prompt": input_text[:1000]},
                    metadata={"model": self.gemini_service.model_name},
                ) as span:
                    # Log API call start
                    logger.log_api_call(
                        "gemini",
                        "generate_response",
                        session_id,
                        agent_name=agent_name,
                        system_prompt_length=len(self.system_prompt),
                        input_length=len(input_text),
                    )

                    api_start_time = time.time()

                    # Scan input for prompt injection (LLM Guard)
                    llm_guard = get_llm_guard_scanner()
                    input_safe, sanitized_input, input_issues = llm_guard.scan_input(
                        input_text
                    )

                    if not input_safe:
                        logger.security_event(
                            "input_blocked",
                            agent_name=agent_name,
                            session_id=session_id,
                            issues=input_issues,
                        )
                        raise ValueError(
                            "Input blocked due to potential prompt injection"
                        )

                    try:
                        # Use mock service if enabled
                        if self.mock_service:
                            logger.debug(
                                "Using mock Gemini service",
                                session_id=session_id,
                                agent_name=agent_name,
                            )
                            response = self.mock_service.generate_response(
                                system_prompt=self.system_prompt,
                                user_input=input_text,
                                context=context,
                            )
                        else:
                            # Use real Gemini service
                            logger.debug(
                                "Using real Gemini service",
                                session_id=session_id,
                                agent_name=agent_name,
                            )
                            response = self.gemini_service.generate_response(
                                system_prompt=self.system_prompt,
                                user_input=input_text,
                                context=context,
                            )

                        span.update(output=response)
                        api_execution_time = time.time() - api_start_time

                        # Log successful API call
                        logger.debug(
                            "Gemini API call completed",
                            session_id=session_id,
                            agent_name=agent_name,
                            execution_time_ms=round(api_execution_time * 1000, 2),
                            response_length=len(response),
                            response_preview=response[:100] + "..."
                            if len(response) > 100
                            else response,
                        )

                        # Scan output with LLM Guard
                        output_safe, llm_guard_output, output_issues = (
                            llm_guard.scan_output(response)
                        )
                        if not output_safe:
                            logger.security_event(
                                "output_sensitive_detected",
                                agent_name=agent_name,
                                session_id=session_id,
                                issues=output_issues,
                            )

                        # Sanitize output with OutputSanitizer (defense in depth)
                        sanitizer = get_output_sanitizer()
                        is_safe, sanitized_response, issues = sanitizer.sanitize(
                            response
                        )

                        if not is_safe:
                            logger.security_event(
                                "output_sanitization_blocked",
                                agent_name=agent_name,
                                session_id=session_id,
                                issues=issues,
                            )

                        return sanitized_response

                    except Exception as e:
                        api_execution_time = time.time() - api_start_time
                        trace.update(output={"error": "exception", "message": str(e)})
                        logger.log_agent_error(agent_name, e, session_id)
                        logger.error(
                            "Gemini API call failed",
                            session_id=session_id,
                            agent_name=agent_name,
                            execution_time_ms=round(api_execution_time * 1000, 2),
                            error_type=type(e).__name__,
                            error_message=str(e),
                        )
                        raise

    T = TypeVar("T", bound=BaseModel)

    def parse_and_validate(self, raw_result: str | None, model: Type[T]) -> T:
        """Parse raw Gemini output and validate it against a Pydantic model.

        Raises ValueError on empty/unparseable output, ValidationError on schema mismatch.
        """
        if not raw_result or not raw_result.strip():
            raise ValueError("Empty response received from Gemini API")

        parsed = parse_json_object(raw_result)
        if not parsed:
            raise ValueError(
                f"Failed to parse JSON from Gemini response: {raw_result[:200]}"
            )

        return model.model_validate(parsed)
