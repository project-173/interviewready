"""Job Alignment Agent implementation."""

import json
import time
from typing import List, Dict, Any

from .base import BaseAgent
from ..core.langfuse_client import trace_agent_process
from ..core.logging import logger
from ..models.agent import AgentResponse, AlignmentReport
from ..models.session import SessionContext
from ..utils.json_parser import parse_json_object


class JobAlignmentAgent(BaseAgent):
    """Agent for evaluating how well a resume matches a specific job description."""

    USE_MOCK_RESPONSE = False
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
        """Initialize Job Alignment Agent.

        Args:
            gemini_service: Gemini API service
        """
        super().__init__(
            gemini_service=gemini_service,
            system_prompt=self.SYSTEM_PROMPT,
            name="JobAlignmentAgent",
        )

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

    def _compute_confidence(self, fit_score: int, missing_skills: List[str]) -> float:
        """Compute confidence score from fit score and missing skills count."""
        base = fit_score / 100.0
        penalty = len(missing_skills) * 0.02
        return max(0.3, min(0.95, base - penalty))

    def _normalize_alignment_output(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize parsed content into AlignmentReport schema."""
        data = {
            "skillsMatch": parsed.get("skillsMatch", []),
            "missingSkills": parsed.get("missingSkills", []),
            "experienceMatch": (
                parsed.get("experienceMatch")
                if isinstance(parsed.get("experienceMatch"), str)
                else ""
            ),
            "fitScore": int(parsed.get("fitScore", 50)) if str(parsed.get("fitScore", "")).strip() else 50,
            "reasoning": parsed.get("reasoning") if isinstance(parsed.get("reasoning"), str) else "No reasoning provided.",
        }
        try:
            validated = AlignmentReport.model_validate(data)
            return validated.model_dump()
        except Exception:
            fallback = AlignmentReport(
                skillsMatch=[],
                missingSkills=[],
                experienceMatch="",
                fitScore=50,
                reasoning="No reasoning provided.",
            )
            return fallback.model_dump()

    @trace_agent_process
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
            input_preview=input_text[:100] + "..." if len(input_text) > 100 else input_text,
        )

        try:
            raw_output = None
            if self.USE_MOCK_RESPONSE:
                raw_output = self.get_mock_response_by_key(self.MOCK_RESPONSE_KEY)
                if raw_output is None:
                    logger.warning(
                        "JobAlignmentAgent mock enabled but response key not found",
                        session_id=session_id,
                        mock_response_key=self.MOCK_RESPONSE_KEY,
                    )

            if raw_output is None:
                raw_output = self.call_gemini(input_text, context)

            processing_time = time.time() - processing_start_time
            logger.debug(
                "JobAlignmentAgent LLM call completed",
                session_id=session_id,
                processing_time_ms=round(processing_time * 1000, 2),
                raw_output_length=len(raw_output),
            )

            parsed = self._parse_json(raw_output)
            normalized = self._normalize_alignment_output(parsed)

            logger.debug(
                "JobAlignmentAgent JSON parsing completed",
                session_id=session_id,
                parsing_successful=bool(parsed),
                parsed_keys=list(parsed.keys()) if parsed else [],
            )

            skills_match: List[str] = normalized.get("skillsMatch", [])
            missing_skills: List[str] = normalized.get("missingSkills", [])
            fit_score: int = int(normalized.get("fitScore", 50))
            reasoning: str = normalized.get("reasoning", "No reasoning provided.")

            logger.debug(
                "JobAlignmentAgent analysis results",
                session_id=session_id,
                skills_match_count=len(skills_match),
                missing_skills_count=len(missing_skills),
                fit_score=fit_score,
                reasoning_length=len(reasoning),
            )

            confidence = self._compute_confidence(fit_score, missing_skills)

            logger.debug(
                "JobAlignmentAgent confidence calculated",
                session_id=session_id,
                confidence_score=confidence,
                base_confidence=fit_score / 100.0,
                penalty=len(missing_skills) * 0.02,
            )

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
                "experienceMatch": normalized.get("experienceMatch", ""),
                "agentVersion": "1.0",
            }

            response = AgentResponse(
                agent_name=self.get_name(),
                content=json.dumps(normalized, indent=2),
                reasoning=reasoning,
                confidence_score=confidence,
                decision_trace=decision_trace,
                sharp_metadata=metadata,
            )

            logger.debug(
                "JobAlignmentAgent response created",
                session_id=session_id,
                confidence_score=confidence,
                fit_score=fit_score,
                analysis_type="job_alignment",
            )

            return response

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
