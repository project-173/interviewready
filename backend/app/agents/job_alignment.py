"""Job Alignment Agent implementation."""

import json
import time
from typing import List, Dict, Any
from langfuse import observe

from .base import BaseAgent
from langfuse import observe
from ..core.logging import logger
from ..core.config import settings
from ..models.agent import AgentResponse, AlignmentReport
from ..models.session import SessionContext
from ..utils.json_parser import parse_json_object


from ..core.constants import ANTI_JAILBREAK_DIRECTIVE


class JobAlignmentAgent(BaseAgent):
    """Agent for evaluating how well a resume matches a specific job description."""

    USE_MOCK_RESPONSE = settings.MOCK_JOB_ALIGNMENT_AGENT
    MOCK_RESPONSE_KEY = "JobAlignmentAgent"

    SYSTEM_PROMPT = (
        """
        You are a Job Description Alignment Agentthat compares candidate resumes against job descriptions.

CRITICAL OUTPUT REQUIREMENT: You MUST respond with ONLY a valid JSON object. No text before, after, or around the JSON.

RULES:
1. Your entire response must be exactly one JSON object
2. Start with '{' and end with '}' - nothing else
3. Do NOT include any markdown code blocks (no ```json or ```)
4. Do NOT include any explanatory text, preamble, or summary
5. Do NOT include comments (// or /* */)
6. Every field must be present and valid
7. Array fields must contain 2+ non-empty items minimum
8. Score must be a number between 0-100
9. Do NOT use null values - use empty strings or empty arrays instead

RESPOND WITH THIS EXACT JSON STRUCTURE AND NOTHING ELSE:
{
  "alignment_score": 82,
  "matching_skills": ["skill 1", "skill 2", "skill 3"],
  "missing_skills": ["skill 1", "skill 2"],
  "gap_severity": {
    "critical": ["gap 1"],
    "important": ["gap 1", "gap 2"],
    "nice_to_have": ["gap 1", "gap 2"]
  },
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "gaps": ["gap 1", "gap 2", "gap 3"],
  "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"],
  "time_to_proficiency_months": 6
}
"""
        + ANTI_JAILBREAK_DIRECTIVE
    )

    def __init__(self, gemini_service):
        """Initialize Job Alignment Agent.

        Args:
            gemini_service: Gemini API service
        """
        super().__init__(
            gemini_service=gemini_service,
            system_prompt=self.SYSTEM_PROMPT,
            name="JobAlignmentAgent",
        )

    @observe(name="parse-json", as_type="tool")
    def _parse_json(self, raw: str) -> Dict[str, Any]:
        """Parse JSON string into a dict, returning empty dict on failure."""
        session_id = "unknown"  # We don't have session context here

        result = parse_json_object(raw)
        if result:
            logger.debug(
                "JobAlignmentAgent JSON parsing successful",
                session_id=session_id,
                keys_found=list(result.keys()),
            )
        else:
            logger.warning(
                "JobAlignmentAgent JSON parsing failed, returning empty dict",
                session_id=session_id,
                raw_preview=raw[:200],
            )
        return result

    @observe(name="compute-confidence", as_type="tool")
    def _compute_confidence(self, fit_score: int, missing_skills: List[str]) -> float:
        """Compute confidence score from fit score and missing skills count."""
        base = fit_score / 100.0
        penalty = len(missing_skills) * 0.02
        return max(0.3, min(0.95, base - penalty))

    @observe(name="job_alignment_process", as_type="agent")
    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        """Process resume and job description to evaluate alignment.

        Args:
            input_text: Resume text (also used as job description placeholder here)
            context: Session context

        Returns:
            Agent response with alignment evaluation
        """
        session_id = getattr(context, "session_id", "unknown")
        agent_name = self.get_name()
        processing_start_time = time.time()

        logger.debug(
            "JobAlignmentAgent processing started",
            session_id=session_id,
            input_length=len(input_text),
            input_preview=input_text[:100] + "..."
            if len(input_text) > 100
            else input_text,
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

            if not raw_result or not raw_result.strip():
                raise ValueError("Empty response received from Gemini API")

            processing_time = time.time() - processing_start_time

            logger.debug(
                "JobAlignmentAgent JSON parsing completed",
                session_id=session_id,
                processing_time_ms=round(processing_time * 1000, 2),
            )

            skills_match: List[str] = structured_result.get("skillsMatch", [])
            missing_skills: List[str] = structured_result.get("missingSkills", [])
            fit_score: int = int(structured_result.get("fitScore", 50))
            reasoning: str = structured_result.get(
                "reasoning", "No reasoning provided."
            )

            confidence = self._compute_confidence(fit_score, missing_skills)
            decision_trace = [
                "Parsed LLM output",
                f"Identified {len(skills_match)} matching skills",
                f"Identified {len(missing_skills)} missing skills",
                f"Computed fit score: {fit_score}",
            ]

            metadata = {
                "fitScore": fit_score,
                "skillsMatch": skills_match,
                "missingSkills": missing_skills,
                "experienceMatch": structured_result.get("experienceMatch", ""),
                "agentVersion": "1.0",
            }

            return AgentResponse(
                agent_name=self.get_name(),
                content=json.dumps(structured_result, indent=2),
                reasoning=reasoning,
                confidence_score=confidence,
                decision_trace=decision_trace,
                sharp_metadata=metadata,
            )

        except Exception as e:
            processing_time = time.time() - processing_start_time
            logger.log_agent_error(agent_name, e, session_id)
            logger.error(
                "JobAlignmentAgent processing failed",
                session_id=session_id,
                processing_time_ms=round(processing_time * 1000, 2),
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise
