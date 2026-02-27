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

        You MUST return ONLY valid JSON.
        Do NOT wrap in markdown.
        Do NOT add explanation outside JSON.

        Return format:

        {
        "skillsMatch": [],
        "missingSkills": [],
        "experienceMatch": "",
        "fitScore": 0,
        "reasoning": ""
        }
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

    def _call_llm(self, resume: str, job_desc: str, context: SessionContext) -> str:
        """Call LLM — currently returns hardcoded mock response."""

        user_input = f"""
            Resume:
            {resume}

            Job Description:
            {job_desc}

            Return ONLY valid JSON.
        """

        return self.gemini_service.generate_response(
            system_prompt=self.SYSTEM_PROMPT,
            user_input=user_input,
            context=context
        )

        # return """
        # {
        #     "skillsMatch": ["Java", "Spring Boot"],
        #     "missingSkills": ["AWS", "Kubernetes"],
        #     "experienceMatch": "Strong backend experience",
        #     "fitScore": 78,
        #     "reasoning": "Good backend alignment but missing cloud exposure."
        # }
        # """

    def _parse_json(self, raw: str) -> Dict[str, Any]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            cleaned = re.sub(r"```json|```", "", raw).strip()
            try:
                return json.loads(cleaned)
            except:
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

        resume = input_text
        job_desc = context.job_description or ""

        raw_output = self._call_llm(resume, job_desc, context)

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