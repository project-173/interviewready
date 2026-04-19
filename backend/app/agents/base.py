"""Base agent classes and protocols."""

import json
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, Protocol, TypeVar

from langfuse import Langfuse, propagate_attributes
from pydantic import BaseModel

from app.core.logging import logger
from app.models.agent import AgentInput, AgentResponse
from app.models.session import SessionContext
from app.security.llm_guard_scanner import get_llm_guard_scanner
from app.utils.json_parser import parse_json_object
from app.utils.output_sanitizer import get_output_sanitizer

langfuse = Langfuse()


class BaseAgentProtocol(Protocol):
    """Protocol defining the interface for all agents."""

    def get_name(self) -> str: ...
    def process(
        self, input_data: AgentInput | str | bytes, context: SessionContext
    ) -> AgentResponse: ...
    def update_system_prompt(self, new_prompt: str) -> None: ...
    def get_system_prompt(self) -> str: ...


class BaseAgent(ABC, BaseAgentProtocol):
    """Abstract base agent implementation."""

    MOCK_RESPONSES_FILE = Path(__file__).resolve().parents[1] / "mock_responses.json"
    _mock_responses_cache: dict[str, Any] | None = None

    def __init__(self, gemini_service, system_prompt: str, name: str):
        self.gemini_service = gemini_service
        self.system_prompt = system_prompt
        self.name = name
        self.mock_service = None

    def get_name(self) -> str:
        return self.name

    def update_system_prompt(self, new_prompt: str) -> None:
        self.system_prompt = new_prompt

    def get_system_prompt(self) -> str:
        return self.system_prompt

    @abstractmethod
    def process(
        self, input_data: AgentInput | str | bytes, context: SessionContext
    ) -> AgentResponse:
        """Process input and return agent response. Must be implemented by subclasses."""

    @classmethod
    def _load_mock_responses(cls) -> dict[str, Any]:
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
                error=str(e),
            )

        cls._mock_responses_cache = {}
        return cls._mock_responses_cache

    def get_mock_response_by_key(self, key: str) -> str | None:
        responses = self._load_mock_responses()
        value = responses.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, (dict, list)):
            return json.dumps(value, indent=2)
        return None

    def call_gemini(
        self,
        input_text: str,
        context: SessionContext,
        tools: list[Callable] | None = None,
    ) -> str:
        session_id = getattr(context, "session_id", "unknown")
        agent_name = self.get_name()
        user_id = getattr(context, "user_id", None)

        def _wrap_tool(tool: Callable) -> Callable:
            if not callable(tool):
                return tool

            tool_name = getattr(tool, "__name__", type(tool).__name__)

            @wraps(tool)
            def _wrapped(*args, **kwargs):
                logger.debug(
                    "Gemini tool call started",
                    session_id=session_id,
                    agent_name=agent_name,
                    tool_name=tool_name,
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys()),
                )
                tool_start = time.time()
                result = tool(*args, **kwargs)
                tool_elapsed = time.time() - tool_start
                logger.debug(
                    "Gemini tool call completed",
                    session_id=session_id,
                    agent_name=agent_name,
                    tool_name=tool_name,
                    execution_time_ms=round(tool_elapsed * 1000, 2),
                )
                return result

            return _wrapped

        wrapped_tools = [_wrap_tool(tool) for tool in tools] if tools else None

        with (
            langfuse.start_as_current_observation(
                as_type="span",
                name=f"{agent_name}_llm_call",
                metadata={"agent": agent_name, "prompt_length": len(input_text)},
            ) as trace,
            propagate_attributes(user_id=user_id, session_id=session_id),
        ):
            with trace.start_as_current_observation(
                as_type="span",
                name="call_gemini",
                input={"prompt": input_text[:1000]},
                metadata={"model": self.gemini_service.model_name},
            ) as span:
                logger.log_api_call(
                    "gemini",
                    "generate_response",
                    session_id,
                    agent_name=agent_name,
                    system_prompt_length=len(self.system_prompt),
                    input_length=len(input_text),
                )

                api_start_time = time.time()

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
                    msg = "Input blocked due to potential prompt injection"
                    raise ValueError(msg)

                try:
                    if self.mock_service:
                        logger.debug(
                            "Using mock Gemini service",
                            session_id=session_id,
                            agent_name=agent_name,
                        )
                        response = self.mock_service.generate_response(
                            system_prompt=self.system_prompt,
                            user_input=sanitized_input,
                            tools=wrapped_tools,
                        )
                    else:
                        logger.debug(
                            "Using real Gemini service",
                            session_id=session_id,
                            agent_name=agent_name,
                        )
                        response = self.gemini_service.generate_response(
                            system_prompt=self.system_prompt,
                            user_input=sanitized_input,
                            tools=wrapped_tools,
                        )

                    if response is None:
                        logger.warning(
                            "Gemini response was None",
                            session_id=session_id,
                            agent_name=agent_name,
                        )
                        response = ""
                    elif not isinstance(response, str):
                        response = str(response)

                    span.update(output=response)
                    api_execution_time = time.time() - api_start_time

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

                    output_safe, _, output_issues = llm_guard.scan_output(response)
                    if not output_safe:
                        logger.security_event(
                            "output_sensitive_detected",
                            agent_name=agent_name,
                            session_id=session_id,
                            issues=output_issues,
                        )

                    sanitizer = get_output_sanitizer()
                    is_safe, sanitized_response, issues = sanitizer.sanitize(response)

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

    def parse_and_validate(self, raw_result: str | None, model: type[T]) -> T:
        if not raw_result or not raw_result.strip():
            msg = "Empty response received from Gemini API"
            raise ValueError(msg)

        parsed = parse_json_object(raw_result)
        if not parsed:
            msg = f"Failed to parse JSON from Gemini response: {raw_result[:200]}"
            raise ValueError(msg)

        return model.model_validate(parsed)
