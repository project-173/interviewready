"""Interview Coach Agent implementation."""

import time
from typing import Optional
from langfuse import observe
from .base import BaseAgent
from .gemini_service import GeminiLiveService
from ..core.logging import logger
from ..core.config import settings
from ..models.agent import AgentResponse
from ..models.session import SessionContext


class InterviewCoachAgent(BaseAgent):
    """Agent for providing interview coaching and simulation."""

    USE_MOCK_RESPONSE = False
    MOCK_RESPONSE_KEY = "InterviewCoachAgent"

    SYSTEM_PROMPT = """You are an expert Interview Coach specializing in personalized interview preparation. You have access to the candidate's resume and the target job description. Your role is to:

        1. Analyze the candidate's resume to understand their background, skills, and experience
        2. Review the job description to identify key requirements, responsibilities, and qualifications
        3. Provide tailored interview coaching that bridges the gap between the candidate's profile and job requirements
        4. Simulate realistic interview scenarios based on the job description
        5. Give constructive feedback on responses, highlighting strengths and areas for improvement
        6. For audio inputs, analyze speech clarity, confidence, and content delivery
        7. Suggest specific preparation strategies to address skill gaps or experience mismatches

        Always provide actionable, encouraging feedback that helps the candidate succeed in their job interview."""
    CONFIDENCE_SCORE = 0.85
    # Use the global Gemini model configured in settings (GEMINI_MODEL) for both standard and live calls.
    # This ensures interview coaching uses the same model as other agents unless overridden via env vars.
    DEFAULT_MODEL = settings.GEMINI_MODEL

    def __init__(self, gemini_service):
        """Initialize Interview Coach Agent.

        Args:
            gemini_service: Gemini API service
        """
        super().__init__(
            gemini_service=gemini_service,
            system_prompt=self.SYSTEM_PROMPT,
            name="InterviewCoachAgent",
        )

        if self.USE_MOCK_RESPONSE:
            self.gemini_live_service = None
        else:
            self.gemini_live_service = GeminiLiveService()

            # Try to connect to Gemini Live if API key is available
            api_key = settings.GEMINI_API_KEY
            if api_key and api_key.strip():
                try:
                    self.gemini_live_service.connect(api_key, self.DEFAULT_MODEL)
                except Exception as e:
                    print(f"Failed to connect to Gemini Live: {e}")
            else:
                print("GEMINI_API_KEY not set; Gemini Live will not be used.")
    
    @observe
    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        """Process interview coaching request.

        Args:
            input_text: Interview question or coaching request
            context: Session context

        Returns:
            Agent response with interview coaching feedback
        """
        session_id = getattr(context, "session_id", "unknown")
        agent_name = self.get_name()
        processing_start_time = time.time()
        input_type = "audio" if isinstance(input_text, bytes) else "text"

        # Log processing start
        logger.debug(
            f"InterviewCoachAgent processing started",
            session_id=session_id,
            input_type=input_type,
            input_length=len(input_text),
            input_preview=(
                input_text[:100].decode("utf-8", errors="ignore") + "..."
                if isinstance(input_text, bytes) and len(input_text) > 100
                else (
                    input_text.decode("utf-8", errors="ignore")
                    if isinstance(input_text, bytes)
                    else (
                        input_text[:100] + "..."
                        if len(input_text) > 100
                        else input_text
                    )
                )
            ),
        )

        try:
            if isinstance(input_text, bytes):
                # Handle audio input
                gemini_live_available = (
                    hasattr(self.gemini_live_service, "connected")
                    and self.gemini_live_service.connected
                )
                logger.debug(
                    f"InterviewCoachAgent processing audio input",
                    session_id=session_id,
                    gemini_live_available=gemini_live_available,
                    audio_length=len(input_text),
                )

                if gemini_live_available:
                    result = self._call_gemini_live_audio(
                        input_text, self.system_prompt, context
                    )
                    method_used = "gemini_live_audio"
                else:
                    result = "Audio processing is not available. Please ensure Gemini Live is connected."
                    method_used = "audio_unavailable"
            else:
                # Handle text input
                if self.USE_MOCK_RESPONSE:
                    result = self.get_mock_response_by_key(self.MOCK_RESPONSE_KEY)
                    if result is None:
                        logger.warning(
                            "InterviewCoachAgent mock enabled but response key not found",
                            session_id=session_id,
                            mock_response_key=self.MOCK_RESPONSE_KEY,
                        )
                        result = self.call_gemini(input_text, context)
                        method_used = "standard_gemini_fallback"
                    else:
                        method_used = "mock_response_file"
                else:
                    # Try to use Gemini Live first, fallback to regular Gemini
                    gemini_live_available = (
                        hasattr(self.gemini_live_service, "connected")
                        and self.gemini_live_service.connected
                    )
                    logger.debug(
                        f"InterviewCoachAgent checking Gemini Live availability",
                        session_id=session_id,
                        gemini_live_available=gemini_live_available,
                    )

                    if gemini_live_available:
                        logger.debug(
                            f"InterviewCoachAgent using Gemini Live",
                            session_id=session_id,
                        )
                        result = self._call_gemini_live(input_text, context)
                        if not result or result.startswith("Error"):
                            logger.warning(
                                f"InterviewCoachAgent Gemini Live failed, falling back to standard Gemini",
                                session_id=session_id,
                                result_preview=result[:100] if result else "No result",
                            )
                            # Fallback to regular Gemini
                            result = self.call_gemini(input_text, context)
                            method_used = "standard_gemini_fallback"
                        else:
                            method_used = "gemini_live"
                    else:
                        logger.debug(
                            f"InterviewCoachAgent using standard Gemini (Live unavailable)",
                            session_id=session_id,
                        )
                        # Fallback to regular Gemini
                        result = self.call_gemini(input_text, context)
                        method_used = "standard_gemini"

            processing_time = time.time() - processing_start_time
            logger.debug(
                f"InterviewCoachAgent processing completed",
                session_id=session_id,
                input_type=input_type,
                processing_time_ms=round(processing_time * 1000, 2),
                method_used=method_used,
                result_length=len(result),
                result_preview=result[:100] + "..." if len(result) > 100 else result,
            )

            # Build decision trace for auditability
            input_type = "audio" if isinstance(input_text, bytes) else "text"
            decision_trace = [
                f"InterviewCoachAgent: Generated interview coaching feedback for {input_type} input",
                f"InterviewCoachAgent: Used coaching model with confidence {self.CONFIDENCE_SCORE}",
                f"InterviewCoachAgent: Method used: {method_used}",
            ]

            # Add method used to trace
            if method_used == "gemini_live":
                decision_trace.append(
                    "InterviewCoachAgent: Used Gemini Live for real-time response"
                )
            elif method_used == "gemini_live_audio":
                decision_trace.append(
                    "InterviewCoachAgent: Used Gemini Live for audio analysis and feedback"
                )
            elif method_used == "mock_response_file":
                decision_trace.append(
                    "InterviewCoachAgent: Used mock response from backend/mock_responses.json"
                )
            elif method_used == "audio_unavailable":
                decision_trace.append(
                    "InterviewCoachAgent: Audio processing unavailable due to missing Gemini Live connection"
                )
            else:
                decision_trace.append(
                    "InterviewCoachAgent: Used standard Gemini API (fallback)"
                )

            # Create SHARP metadata
            analysis_type = (
                "interview_coaching_audio"
                if input_type == "audio"
                else "interview_coaching"
            )
            sharp_metadata = {
                "analysis_type": analysis_type,
                "confidence_score": self.CONFIDENCE_SCORE,
                "gemini_live_available": (
                    method_used in ["gemini_live", "gemini_live_audio"]
                ),
                "method_used": method_used,
                "input_type": input_type,
            }

            response = AgentResponse(
                agent_name=self.get_name(),
                content=result,
                reasoning="Generated interview coaching feedback.",
                confidence_score=self.CONFIDENCE_SCORE,
                decision_trace=decision_trace,
                sharp_metadata=sharp_metadata,
            )

            # Log response creation
            logger.debug(
                f"InterviewCoachAgent response created",
                session_id=session_id,
                input_type=input_type,
                confidence_score=self.CONFIDENCE_SCORE,
                analysis_type=analysis_type,
                method_used=method_used,
            )

            return response

        except Exception as e:
            processing_time = time.time() - processing_start_time
            logger.log_agent_error(agent_name, e, session_id)
            logger.error(
                f"InterviewCoachAgent processing failed",
                session_id=session_id,
                processing_time_ms=round(processing_time * 1000, 2),
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise

    def _call_gemini_live_audio(
        self, audio_data: bytes, system_prompt: str, context: Optional[SessionContext] = None
    ) -> Optional[str]:
        """Call Gemini Live service with audio data.

        Args:
            audio_data: Audio data as bytes
            system_prompt: System prompt
            context: Session context (used to add analysis history and resume/job info)

        Returns:
            Response from Gemini Live or None if error
        """
        session_id = getattr(context, "session_id", "unknown")

        if (
            not hasattr(self.gemini_live_service, "connected")
            or not self.gemini_live_service.connected
        ):
            logger.debug(
                "InterviewCoachAgent Gemini Live not connected", session_id=session_id
            )
            return None

        try:
            logger.debug(
                "InterviewCoachAgent calling Gemini Live with audio",
                session_id=session_id,
                audio_length=len(audio_data),
            )

            # Build a small text prompt that includes prior analysis/context so the audio response is grounded.
            text_prompt = """
This is a follow-up audio response from the user. Use the resume, job description, and previous analysis results to provide coaching feedback.
"""
            if context:
                # Reuse the same prompt construction logic used for standard Gemini calls
                try:
                    text_prompt = self.gemini_service._construct_user_message(
                        text_prompt, context
                    )
                except Exception:
                    pass

            # Send audio and wait for response (10s timeout)
            live_start_time = time.time()
            raw = self.gemini_live_service.send_audio_and_wait_response(
                audio_data, system_prompt, text_prompt=text_prompt, timeout_ms=10000
            )
            live_execution_time = time.time() - live_start_time

            if not raw or raw.strip() == "":
                logger.warning(
                    "InterviewCoachAgent Gemini Live audio returned empty response",
                    session_id=session_id,
                    execution_time_ms=round(live_execution_time * 1000, 2),
                )
                return "(No response from Gemini Live for audio)"

            logger.debug(
                "InterviewCoachAgent Gemini Live audio call successful",
                session_id=session_id,
                execution_time_ms=round(live_execution_time * 1000, 2),
                response_length=len(raw),
                response_preview=raw[:100] + "..." if len(raw) > 100 else raw,
            )

            return raw
        except Exception as e:
            logger.log_agent_error("InterviewCoachAgent-GeminiLiveAudio", e, session_id)
            logger.error(
                "InterviewCoachAgent Gemini Live audio call failed",
                session_id=session_id,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return f"Error contacting Gemini Live for audio: {str(e)}"

    def _call_gemini_live(
        self, input_text: str, context: Optional[SessionContext] = None
    ) -> Optional[str]:
        """Call Gemini Live service with text input.

        Args:
            input_text: User input text
            context: Session context (used to include prior analysis + history)

        Returns:
            Response from Gemini Live or None if error
        """
        session_id = getattr(context, "session_id", "unknown")

        if (
            not hasattr(self.gemini_live_service, "connected")
            or not self.gemini_live_service.connected
            or not getattr(self.gemini_live_service, "client", None)
        ):
            logger.debug(
                "InterviewCoachAgent Gemini Live not connected",
                session_id=session_id,
            )
            return None

        try:
            logger.debug(
                "InterviewCoachAgent calling Gemini Live with text",
                session_id=session_id,
                input_length=len(input_text),
            )

            from google.genai import types

            live_start_time = time.time()
            # Build a prompt that includes context (resume, job, analysis results) when available.
            user_prompt = input_text
            if context:
                try:
                    user_prompt = self.gemini_service._construct_user_message(
                        input_text, context
                    )
                except Exception:
                    # Fallback to raw input_text if prompt construction fails.
                    user_prompt = input_text

            response = self.gemini_live_service.client.models.generate_content(
                model=self.gemini_live_service.model_name,
                contents=[user_prompt],
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                ),
            )
            live_execution_time = time.time() - live_start_time

            raw = getattr(response, "text", None) or ""
            if not raw or raw.strip() == "":
                logger.warning(
                    "InterviewCoachAgent Gemini Live returned empty response",
                    session_id=session_id,
                    execution_time_ms=round(live_execution_time * 1000, 2),
                )
                return "(No response from Gemini Live)"

            logger.debug(
                "InterviewCoachAgent Gemini Live text call successful",
                session_id=session_id,
                execution_time_ms=round(live_execution_time * 1000, 2),
                response_length=len(raw),
                response_preview=raw[:100] + "..." if len(raw) > 100 else raw,
            )

            return raw
        except Exception as e:
            logger.log_agent_error("InterviewCoachAgent-GeminiLive", e, session_id)
            logger.error(
                "InterviewCoachAgent Gemini Live text call failed",
                session_id=session_id,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return f"Error contacting Gemini Live: {str(e)}"
