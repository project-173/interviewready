"""Job Alignment Agent implementation."""

import json
from typing import List, Dict, Any
from .base import BaseAgent
from ..models.agent import AgentResponse
from ..models.session import SessionContext


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
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _compute_confidence(self, fit_score: int, missing_skills: List[str]) -> float:
        """Compute confidence score from fit score and missing skills count."""
        base = fit_score / 100.0
        penalty = len(missing_skills) * 0.02
        return max(0.3, min(0.95, base - penalty))

    def _build_human_readable_output(
        self, fit_score: int, matched: List[str], missing: List[str]
    ) -> str:
        """Build a human-readable alignment summary string."""
        return (
            "JD Alignment Summary\n"
            "--------------------\n"
            f"Fit Score: {fit_score}/100\n\n"
            "Matched Skills:\n"
            f"{', '.join(matched)}\n\n"
            "Missing Skills:\n"
            f"{', '.join(missing)}\n"
        )

    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        """Process resume and job description to evaluate alignment.

        Args:
            input_text: Resume text (also used as job description placeholder here)
            context: Session context

        Returns:
            Agent response with alignment evaluation
        """
        final_prompt = self._get_final_prompt(input_text, input_text)

        raw_output = self._call_llm(final_prompt)

        # ---- Parse LLM JSON ----
        parsed = self._parse_json(raw_output)

        skills_match: List[str] = parsed.get("skillsMatch", [])
        missing_skills: List[str] = parsed.get("missingSkills", [])
        fit_score: int = int(parsed.get("fitScore", 50))
        reasoning: str = parsed.get("reasoning", "No reasoning provided.")

        # ---- Confidence logic ----
        confidence = self._compute_confidence(fit_score, missing_skills)

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
            "agentVersion": "1.0",
        }

        return AgentResponse(
            agent_name=self.get_name(),
            content=self._build_human_readable_output(fit_score, skills_match, missing_skills),
            reasoning=reasoning,
            confidence_score=confidence,
            decision_trace=decision_trace,
            sharp_metadata=metadata,
        )