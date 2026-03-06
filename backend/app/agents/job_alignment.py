"""Job Alignment Agent implementation."""

import json
import time
from typing import List, Dict, Any
from .base import BaseAgent
from ..core.logging import logger
from ..models.agent import AgentResponse, AlignmentReport
from ..models.session import SessionContext
from .mock_config import MockConfig
from ..utils.json_parser import parse_json_object

class JobAlignmentAgent(BaseAgent):
    """Agent for evaluating how well a resume matches a specific job description."""

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
            name="JobAlignmentAgent"
        )

    def _get_final_prompt(self, resume: str, job_desc: str) -> str:
        """Build the final prompt by appending resume and job description to system prompt."""
        resume_prompt = f"Resume is: {resume}\n\n Job Description is: {job_desc}"
        self.system_prompt = self.system_prompt + "\n\n" + resume_prompt
        return self.system_prompt

    def _call_llm(self, prompt: str) -> str:
        """Call LLM — currently returns hardcoded mock response."""
        return """
        {
            "skillsMatch": ["Java", "Spring Boot"],
            "missingSkills": ["AWS", "Kubernetes"],
            "experienceMatch": "Strong backend experience",
            "fitScore": 78,
            "reasoning": "Good backend alignment but missing cloud exposure."
        }
        """

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

    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        """Process resume and job description to evaluate alignment.

        Args:
            input_text: Resume text (also used as job description placeholder here)
            context: Session context

        Returns:
            Agent response with alignment evaluation
        """
        session_id = getattr(context, 'session_id', 'unknown')
        agent_name = self.get_name()
        processing_start_time = time.time()
        
        # Log processing start
        logger.debug(f"JobAlignmentAgent processing started", 
                    session_id=session_id, 
                    input_length=len(input_text),
                    input_preview=input_text[:100] + "..." if len(input_text) > 100 else input_text)
        
        try:
            # Use mock service if enabled, otherwise use the existing _call_llm method
            if MockConfig.is_mock_enabled():
                logger.debug("JobAlignmentAgent using mock service", session_id=session_id)
                raw_output = self.call_gemini(input_text, context)
            else:
                logger.debug("JobAlignmentAgent using LLM service", session_id=session_id)
                final_prompt = self._get_final_prompt(input_text, input_text)
                raw_output = self._call_llm(final_prompt)
            
            processing_time = time.time() - processing_start_time
            logger.debug(f"JobAlignmentAgent LLM call completed", 
                        session_id=session_id, 
                        processing_time_ms=round(processing_time * 1000, 2),
                        raw_output_length=len(raw_output))

            # ---- Parse LLM JSON ----
            parsed = self._parse_json(raw_output)
            normalized = self._normalize_alignment_output(parsed)
            
            logger.debug(f"JobAlignmentAgent JSON parsing completed", 
                        session_id=session_id, 
                        parsing_successful=bool(parsed),
                        parsed_keys=list(parsed.keys()) if parsed else [])

            skills_match: List[str] = normalized.get("skillsMatch", [])
            missing_skills: List[str] = normalized.get("missingSkills", [])
            fit_score: int = int(normalized.get("fitScore", 50))
            reasoning: str = normalized.get("reasoning", "No reasoning provided.")
            
            # Log analysis results
            logger.debug(f"JobAlignmentAgent analysis results", 
                        session_id=session_id, 
                        skills_match_count=len(skills_match),
                        missing_skills_count=len(missing_skills),
                        fit_score=fit_score,
                        reasoning_length=len(reasoning))

            # ---- Confidence logic ----
            confidence = self._compute_confidence(fit_score, missing_skills)
            
            logger.debug(f"JobAlignmentAgent confidence calculated", 
                        session_id=session_id, 
                        confidence_score=confidence,
                        base_confidence=fit_score / 100.0,
                        penalty=len(missing_skills) * 0.02)

            # ---- Decision trace ----
            decision_trace = [
                "Parsed LLM output",
                f"Identified {len(skills_match)} matching skills",
                f"Identified {len(missing_skills)} missing skills",
                f"Computed fit score: {fit_score}",
            ]

            # ---- Metadata ----
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
            
            # Log response creation
            logger.debug(f"JobAlignmentAgent response created", 
                        session_id=session_id, 
                        confidence_score=confidence,
                        fit_score=fit_score,
                        analysis_type="job_alignment")
            
            return response
            
        except Exception as e:
            processing_time = time.time() - processing_start_time
            logger.log_agent_error(agent_name, e, session_id)
            logger.error(f"JobAlignmentAgent processing failed", 
                        session_id=session_id, 
                        processing_time_ms=round(processing_time * 1000, 2),
                        error_type=type(e).__name__,
                        error_message=str(e))
            raise
