"""Job Alignment Agent implementation."""

import json
import time
from typing import List
from langfuse import observe

from .base import BaseAgent
from ..core.config import settings
from ..core.logging import logger
from ..models.agent import AgentResponse, AlignmentReport
from ..models.session import SessionContext
from ..utils.json_parser import parse_json_object


class JobAlignmentAgent(BaseAgent):
    """Agent for evaluating how well a resume matches a specific job description."""

    USE_MOCK_RESPONSE = settings.MOCK_JOB_ALIGNMENT_AGENT
    MOCK_RESPONSE_KEY = "JobAlignmentAgent"

    SYSTEM_PROMPT = """
        You are a Job Description Alignment Agent.

        Compare the candidate resume against the job description.

        Return structured JSON with:
        - skillsMatch (list)
        - missingSkills (list)
        - experienceMatch (summary)
        - fitScore (0-100 integer)
        - reasoning (short explanation)
    """

    def __init__(self, gemini_service):
        super().__init__(
            gemini_service=gemini_service,
            system_prompt=self.SYSTEM_PROMPT,
            name="JobAlignmentAgent",
        )

    @observe
    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        """Process resume and job description to evaluate alignment."""
        session_id = getattr(context, "session_id", "unknown")
        start_time = time.time()

        logger.debug(
            "JobAlignmentAgent processing started",
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

            structured_result = self.parse_and_validate(
                raw_result, AlignmentReport
            ).model_dump()

            skills_match: List[str] = structured_result["skillsMatch"]
            missing_skills: List[str] = structured_result["missingSkills"]
            fit_score: int = structured_result["fitScore"]

            logger.debug(
                "JobAlignmentAgent processing completed",
                session_id=session_id,
                processing_time_ms=round((time.time() - start_time) * 1000, 2),
            )

            return AgentResponse(
                agent_name=self.get_name(),
                content=structured_result,
                reasoning=structured_result["reasoning"],
                confidence_score=self._compute_confidence(fit_score, missing_skills),
                decision_trace=[
                    "Parsed LLM output",
                    f"Identified {len(skills_match)} matching skills",
                    f"Identified {len(missing_skills)} missing skills",
                    f"Computed fit score: {fit_score}",
                ],
                sharp_metadata={
                    "fitScore": fit_score,
                    "skillsMatch": skills_match,
                    "missingSkills": missing_skills,
                    "experienceMatch": structured_result["experienceMatch"],
                    "agentVersion": "1.0",
                },
            )

        except Exception as e:
            logger.log_agent_error(self.get_name(), e, session_id)
            logger.error(
                "JobAlignmentAgent processing failed",
                session_id=session_id,
                processing_time_ms=round((time.time() - start_time) * 1000, 2),
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise

    def _compute_confidence(self, fit_score: int, missing_skills: List[str]) -> float:
        """Compute confidence score from fit score and missing skills count."""
        base = fit_score / 100.0
        penalty = len(missing_skills) * 0.02
        return max(0.3, min(0.95, base - penalty))
