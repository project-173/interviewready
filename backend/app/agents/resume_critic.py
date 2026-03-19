"""Resume Critic Agent implementation."""

import json
import time
from langfuse import observe
from .base import BaseAgent
from ..core.logging import logger
from ..models.agent import AgentResponse, StructuralAssessment
from ..models.session import SessionContext
from ..utils.json_parser import parse_json_object


class ResumeCriticAgent(BaseAgent):
    """Analyzes resume structure, ATS compatibility, and impact."""

    USE_MOCK_RESPONSE = False
    MOCK_RESPONSE_KEY = "ResumeCriticAgent"
    CONFIDENCE_SCORE = 0.9

    SYSTEM_PROMPT = """
    You are an expert Resume Critic. Analyze the resume for structure, ATS compatibility, and impact.

    Return ONLY valid JSON with this exact schema:
    {
      "score": 0-100 number,
      "readability": "short text summary",
      "formattingRecommendations": ["recommendation 1", "recommendation 2"],
      "suggestions": ["actionable suggestion 1", "actionable suggestion 2"]
    }
    """

    def __init__(self, gemini_service):
        super().__init__(
            gemini_service=gemini_service,
            system_prompt=self.SYSTEM_PROMPT,
            name="ResumeCriticAgent",
        )

    @observe
    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        """Process resume text and return a structural critique."""
        session_id = getattr(context, "session_id", "unknown")
        start_time = time.time()

        logger.debug(
            "ResumeCriticAgent processing started",
            session_id=session_id,
            input_length=len(input_text),
            input_preview=input_text[:100],
        )

        try:
            raw_result = (
                self.get_mock_response_by_key(self.MOCK_RESPONSE_KEY)
                if self.USE_MOCK_RESPONSE
                else None
            )

            if self.USE_MOCK_RESPONSE and raw_result is None:
                logger.warning(
                    "Mock enabled but response key not found",
                    session_id=session_id,
                    mock_response_key=self.MOCK_RESPONSE_KEY,
                )

            raw_result = raw_result or self.call_gemini(input_text, context)

            structured_result = self.parse_and_validate(raw_result, StructuralAssessment).model_dump()

            logger.debug(
                "ResumeCriticAgent processing completed",
                session_id=session_id,
                processing_time_ms=round((time.time() - start_time) * 1000, 2),
            )

            return AgentResponse(
                agent_name=self.get_name(),
                content=json.dumps(structured_result, indent=2),
                reasoning="Analyzed resume structure and content impact.",
                confidence_score=self.CONFIDENCE_SCORE,
                decision_trace=[
                    "ResumeCriticAgent: Analyzed resume structure and content impact",
                    f"ResumeCriticAgent: Generated critique with confidence {self.CONFIDENCE_SCORE}",
                ],
                sharp_metadata={
                    "analysis_type": "resume_critique",
                    "confidence_score": self.CONFIDENCE_SCORE,
                    "ats_compatibility_checked": True,
                },
            )

        except Exception as e:
            logger.log_agent_error(self.get_name(), e, session_id)
            logger.error(
                "ResumeCriticAgent processing failed",
                session_id=session_id,
                processing_time_ms=round((time.time() - start_time) * 1000, 2),
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise