"""Gemini API service for agent interactions."""

import json
import re
from collections.abc import Callable
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.logging import logger

MAX_OUTPUT_TOKENS = 8192


class GeminiService:
    """Service for interacting with Google Gemini API."""

    def __init__(
        self, api_key: str | None = None, model_name: str = "gemini-2.5-flash"
    ):
        """Initialize Gemini service.

        Args:
            api_key: Gemini API key. If None, will use settings
            model_name: Gemini model name to use
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self.client = None
        self.mock_mode = False

        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            # Gracefully degrade to mock mode when API key is not available
            logger.warning("GEMINI_API_KEY not configured - using mock responses")
            self.mock_mode = True

    def generate_response(
        self,
        system_prompt: str,
        user_input: str,
        temperature: float | None = None,
        tools: list[Callable] | None = None,
    ) -> str:
        """Generate response from Gemini.

        Args:
            system_prompt: System prompt for the model
            user_input: User input text
            temperature: Optional generation temperature
            tools: Optional list of Gemini tools/functions

        Returns:
            Generated response text
        """
        response, _ = self.generate_response_with_usage(
            system_prompt=system_prompt,
            user_input=user_input,
            temperature=temperature,
            tools=tools,
        )
        return response

    def generate_response_with_usage(
        self,
        system_prompt: str,
        user_input: str,
        temperature: float | None = None,
        tools: list[Callable] | None = None,
    ) -> tuple[str, dict[str, int] | None]:
        """Generate response from Gemini and return usage if available.

        Args:
            system_prompt: System prompt for the model
            user_input: User input text
            temperature: Optional generation temperature
            tools: Optional list of Gemini tools/functions

        Returns:
            Tuple of (response text, usage details) where usage details may be None.
        """
        if self.mock_mode:
            return self._generate_mock_response(system_prompt, user_input), None

        try:
            response = self._generate_content(
                system_prompt=system_prompt,
                user_input=user_input,
                temperature=temperature,
                tools=tools,
            )
            response_text = self._extract_text(response)
            if response_text is None:
                msg = "Gemini response contained no text"
                raise ValueError(msg)
            usage = self._extract_usage(response)
            return response_text, usage
        except Exception as e:
            logger.error(f"Gemini API call failed: {e!s}")
            return f"Error calling Gemini API: {e!s}", None

    def _generate_content(
        self,
        system_prompt: str,
        user_input: str,
        temperature: float | None = None,
        tools: list[Callable] | None = None,
    ) -> Any:
        config_kwargs = {
            "system_instruction": system_prompt,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        }
        if temperature is not None:
            config_kwargs["temperature"] = temperature
        if tools:
            config_kwargs["tools"] = tools
            config_kwargs["automatic_function_calling"] = (
                types.AutomaticFunctionCallingConfig()
            )
        return self.client.models.generate_content(
            model=self.model_name,
            contents=user_input,
            config=types.GenerateContentConfig(**config_kwargs),
        )

    def _extract_text(self, response: Any) -> str | None:
        if response is None:
            return None

        # Try direct text extraction first
        text = self._extract_direct_text(response)
        if text:
            return text

        # Try extracting from candidates
        return self._extract_text_from_candidates(response)

    def _extract_direct_text(self, response: Any) -> str | None:
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text
        return None

    def _extract_text_from_candidates(self, response: Any) -> str | None:
        candidates = getattr(response, "candidates", None)
        if not candidates:
            return (
                getattr(response, "text", None)
                if isinstance(getattr(response, "text", None), str)
                else None
            )

        parts_text = self._collect_parts_from_candidates(candidates)
        return "".join(parts_text) if parts_text else None

    def _collect_parts_from_candidates(self, candidates: Any) -> list[str]:
        parts_text: list[str] = []
        for candidate in candidates:
            candidate_parts = self._extract_candidate_parts(candidate)
            parts_text.extend(candidate_parts)
        return parts_text

    def _extract_candidate_parts(self, candidate: Any) -> list[str]:
        content = getattr(candidate, "content", None)
        if not content:
            return []

        parts = getattr(content, "parts", None)
        if not parts:
            return []

        return self._extract_valid_parts(parts)

    def _extract_valid_parts(self, parts: Any) -> list[str]:
        valid_parts = []
        for part in parts:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str) and part_text.strip():
                valid_parts.append(part_text)
        return valid_parts

    def _extract_usage(self, response: Any) -> dict[str, int] | None:
        usage = self._get_usage_metadata(response)
        if usage is None:
            return None

        token_counts = self._extract_token_counts(usage)
        return self._build_usage_dict(token_counts)

    def _get_usage_metadata(self, response: Any) -> Any:
        return getattr(response, "usage_metadata", None) or getattr(
            response, "usage", None
        )

    def _extract_token_counts(self, usage: Any) -> dict[str, int | None]:
        return {
            "prompt_tokens": self._find_token_value(
                usage, ["prompt_token_count", "prompt_tokens", "input_tokens"]
            ),
            "completion_tokens": self._find_token_value(
                usage, ["candidates_token_count", "completion_tokens", "output_tokens"]
            ),
            "total_tokens": self._find_token_value(
                usage, ["total_token_count", "total_tokens"]
            ),
        }

    def _find_token_value(self, usage: Any, keys: list[str]) -> int | None:
        for key in keys:
            value = self._extract_value_from_usage(usage, key)
            if value is not None:
                return self._to_int(value)
        return None

    def _extract_value_from_usage(self, usage: Any, key: str) -> Any:
        if isinstance(usage, dict) and key in usage:
            return usage.get(key)
        if hasattr(usage, key):
            return getattr(usage, key)
        return None

    def _to_int(self, value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _build_usage_dict(
        self, token_counts: dict[str, int | None]
    ) -> dict[str, int] | None:
        prompt_tokens = token_counts["prompt_tokens"]
        completion_tokens = token_counts["completion_tokens"]
        total_tokens = token_counts["total_tokens"]

        # Calculate total if missing
        if (
            total_tokens is None
            and prompt_tokens is not None
            and completion_tokens is not None
        ):
            total_tokens = prompt_tokens + completion_tokens

        usage_details = {}
        if prompt_tokens is not None:
            usage_details["prompt_tokens"] = prompt_tokens
        if completion_tokens is not None:
            usage_details["completion_tokens"] = completion_tokens
        if total_tokens is not None:
            usage_details["total_tokens"] = total_tokens

        return usage_details or None

    def _generate_mock_response(self, system_prompt: str, user_input: str) -> str:
        """Generate a mock response based on the system prompt.

        Args:
            system_prompt: System prompt to determine response format
            user_input: User input text

        Returns:
            Mock JSON response
        """
        # Detect response type based on system prompt
        if "interview evaluator" in system_prompt.lower():
            lowered_input = user_input.lower()
            normalized_words = set(re.findall(r"[a-zA-Z']+", lowered_input))
            token_list = re.findall(r"[a-zA-Z']+", lowered_input)
            looks_like_gibberish = len(token_list) == 1 and len(token_list[0]) >= 10
            low_effort_phrases = [
                "ignore previous instructions",
                "i don't know",
            ]
            if (
                any(phrase in lowered_input for phrase in low_effort_phrases)
                or {"hello", "hi", "idk", "nonsence", "nonsense"} & normalized_words
                or looks_like_gibberish
            ):
                mock_data = {
                    "answer_score": 20,
                    "can_proceed": False,
                    "feedback": "This answer is too weak or not responsive to the interview question. Please answer with a specific, relevant example.",
                }
            else:
                mock_data = {
                    "answer_score": 82,
                    "can_proceed": True,
                    "feedback": "This is a solid answer with relevant detail. Keep making the example concrete and outcome-oriented.",
                }
        elif "resume" in system_prompt.lower() and "critic" in system_prompt.lower():
            # Resume Critic mock response
            mock_data = {
                "resume_data": {
                    "title": "Professional Resume",
                    "summary": "Experienced professional with strong background",
                    "contact": {
                        "fullName": "John Doe",
                        "email": "john@example.com",
                        "phone": "555-0123",
                    },
                    "skills": ["Python", "JavaScript", "Project Management"],
                    "experiences": [
                        {
                            "title": "Senior Developer",
                            "company": "Tech Corp",
                            "start_date": "2020-01",
                            "end_date": "present",
                            "description": "Led development of core platform features",
                        }
                    ],
                    "educations": [
                        {
                            "school": "State University",
                            "degree": "BS Computer Science",
                            "start_date": "2015-09",
                            "end_date": "2019-05",
                        }
                    ],
                },
                "critique": {
                    "score": 78,
                    "readability": "Good structure with clear sections",
                    "formattingRecommendations": [
                        "Use bullet points for better readability",
                        "Ensure consistent date formatting",
                    ],
                    "suggestions": [
                        "Add quantifiable metrics to achievements",
                        "Highlight technical skills more prominently",
                    ],
                },
            }
        elif "alignment" in system_prompt.lower():
            # Job Alignment mock response
            mock_data = {
                "alignment_score": 0.82,
                "matching_skills": ["Python", "Project Management"],
                "missing_skills": ["Kubernetes", "Docker"],
                "strengths": [
                    "Strong technical foundation",
                    "Proven leadership experience",
                ],
                "gaps": ["Limited DevOps experience", "No containerization background"],
                "recommendations": [
                    "Learn containerization technologies",
                    "Pursue Docker and Kubernetes certifications",
                ],
            }
        elif "strength" in system_prompt.lower():
            # Content Strength mock response
            mock_data = {
                "overall_score": 75,
                "content_analysis": {
                    "clarity": 8,
                    "relevance": 7,
                    "completeness": 6,
                    "impact": 7,
                },
                "strengths": ["Clear communication", "Well-organized content"],
                "weaknesses": [
                    "Lacks specific metrics",
                    "Could benefit from more examples",
                ],
                "suggestions": [
                    "Add quantifiable results",
                    "Include more specific achievements",
                ],
            }
        else:
            # Generic response
            mock_data = {
                "status": "processed",
                "analysis": "Mock response generated",
                "recommendations": [
                    "Continue professional development",
                    "Expand skill set",
                ],
            }

        return json.dumps(mock_data)


class GeminiLiveService:
    """Service for Gemini Live API with audio support (placeholder implementation)."""

    def __init__(self):
        """Initialize Gemini Live service."""
        self.connected = False
        self.api_key = None
        self.model_name = None
        self.client = None

    def connect(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash",
    ) -> None:
        """Connect to Gemini Live API.

        Args:
            api_key: Gemini API key
            model_name: Model name for live interactions
        """
        try:
            self.api_key = api_key
            self.model_name = model_name
            self.client = genai.Client(api_key=api_key)
            self.connected = True
        except Exception as e:
            self.connected = False
            msg = f"Failed to connect to Gemini Live: {e!s}"
            raise ConnectionError(msg)

    def send_audio_and_wait_response(
        self,
        audio_data: bytes,
        system_prompt: str,
        mime_type: str = "audio/wav",
        text_prompt: str = "",
    ) -> str | None:
        """Send audio data and wait for response using Gemini API.

        Args:
            audio_data: Audio data as bytes
            system_prompt: System prompt for the model
            mime_type: MIME type of the audio (default: audio/wav)
            text_prompt: Optional text prompt to accompany audio
            timeout_ms: Timeout in milliseconds

        Returns:
            Response text or None if error
        """
        if not self.connected or not self.client:
            return None

        try:
            from google.genai import types

            audio_part = types.Part.from_bytes(data=audio_data, mime_type=mime_type)
            contents = [audio_part]
            if text_prompt:
                contents.insert(0, text_prompt)

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                ),
            )
            return response.text
        except Exception as e:
            return f"Error in Gemini Audio: {e!s}"

    def send_text_and_wait_response(
        self, text: str, system_prompt: str = ""
    ) -> str | None:
        """Send text and wait for response using Gemini API.

        Args:
            text: Text to send
            system_prompt: System prompt

        Returns:
            Response text or None if timeout/error
        """
        if not self.connected or not self.client:
            return None

        try:
            from google.genai import types

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                ),
            )
            return response.text
        except Exception as e:
            return f"Error in Gemini: {e!s}"

    def get_live_session(self, system_prompt: str):
        """Create a live session with Gemini Multimodal Live API.

        Note: This is a placeholder for actual WebSocket session management.
        The Google SDK supports 'live' sessions via WebSockets.
        """
        if not self.connected or not self.client:
            return None

        return self.client.models.connect(
            model=self.model_name,
            config=types.LiveConnectConfig(
                system_instruction=system_prompt,
                response_modalities=["audio"],
            ),
        )
