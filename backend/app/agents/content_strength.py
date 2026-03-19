"""Content Strength Agent implementation."""

import json
import time
from typing import Any
from .base import BaseAgent
from ..core.logging import logger
from ..models.agent import AgentResponse, ContentAnalysisReport
from ..models.session import SessionContext
from ..utils.json_parser import parse_json_object
from langfuse import observe


class ContentStrengthAgent(BaseAgent):
    """Analyzes resume content strength, skills reasoning, and evidence quality."""

    USE_MOCK_RESPONSE = False
    MOCK_RESPONSE_KEY = "ContentStrengthAgent"

    SYSTEM_PROMPT = """
        You are a Content Strength & Skills Reasoning Agent. Your role is to analyze resumes to identify key skills, achievements, and evidence of impact.
        
        ## Your Responsibilities
        1. Identify key skills and achievements from the resume
        2. Evaluate the strength of evidence supporting each claim
        3. Suggest stronger phrasing WITHOUT fabricating new content
        4. Apply confidence scoring and consistency checks
        
        ## Evidence Strength Classification
        - HIGH: Quantifiable results (e.g., "increased revenue by 25%", "led team of 12")
        - MEDIUM: Specific details but not quantified (e.g., "led cross-functional team", "implemented new system")
        - LOW: Vague claims (e.g., "improved processes", "worked on various projects")
        
        ## Faithful Transformation Rules
        - NEVER invent new skills, achievements, or experiences
        - NEVER add numbers or metrics that don't exist in the original
        - ONLY suggest phrasing that preserves the original meaning
        - FLAG any suggestion that cannot be directly traced to source content
        - If you cannot improve phrasing without fabrication, mark as faithful=false
        
        ## Output Format
        Return a JSON object with this exact structure:
        {
          "skills": [
            {
              "name": "skill name",
              "category": "Technical|Soft|Domain|Tool",
              "confidenceScore": 0.0-1.0,
              "evidenceStrength": "HIGH|MEDIUM|LOW",
              "evidence": "direct quote from resume supporting this skill"
            }
          ],
          "achievements": [
            {
              "description": "achievement description",
              "impact": "HIGH|MEDIUM|LOW",
              "quantifiable": true|false,
              "confidenceScore": 0.0-1.0,
              "originalText": "original text from resume"
            }
          ],
          "suggestions": [
            {
              "original": "original phrasing from resume",
              "suggested": "improved phrasing (must be faithful to original)",
              "rationale": "why this change improves clarity",
              "faithful": true|false,
              "confidenceScore": 0.0-1.0
            }
          ],
          "hallucinationRisk": 0.0-1.0,
          "summary": "brief summary of analysis"
        }
        
        ## Hallucination Risk Calculation
        - 0.0-0.2: All claims well-evidenced, suggestions fully faithful
        - 0.3-0.5: Some vague claims, minor rewording suggestions
        - 0.6-0.8: Multiple unsupported claims, some aggressive suggestions
        - 0.9-1.0: High risk of fabrication, flag for human review
        """

    def __init__(self, gemini_service):
        super().__init__(
            gemini_service=gemini_service,
            system_prompt=self.SYSTEM_PROMPT,
            name="ContentStrengthAgent",
        )

    @observe
    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        """Process resume text and return a content strength analysis."""
        session_id = getattr(context, "session_id", "unknown")
        start_time = time.time()

        logger.debug(
            "ContentStrengthAgent processing started",
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

            structured_result = self.parse_and_validate(raw_result, ContentAnalysisReport).model_dump()

            overall_confidence = self._calculate_overall_confidence(structured_result)
            hallucination_risk = structured_result["hallucinationRisk"]

            logger.debug(
                "ContentStrengthAgent processing completed",
                session_id=session_id,
                processing_time_ms=round((time.time() - start_time) * 1000, 2),
            )

            return AgentResponse(
                agent_name=self.get_name(),
                content=json.dumps(structured_result, indent=2),
                reasoning=structured_result["summary"],
                confidence_score=overall_confidence,
                decision_trace=[
                    "ContentStrengthAgent: Analyzed resume for skills and achievements",
                    f"ContentStrengthAgent: Identified {len(structured_result["skills"])} skills",
                    f"ContentStrengthAgent: Identified {len(structured_result["achievements"])} achievements",
                    f"ContentStrengthAgent: Generated {len(structured_result["suggestions"])} suggestions",
                    f"ContentStrengthAgent: Hallucination risk: {hallucination_risk}",
                ],
                sharp_metadata={
                    "hallucinationRisk": hallucination_risk,
                    "overallConfidence": overall_confidence,
                },
            )

        except Exception as e:
            logger.log_agent_error(self.get_name(), e, session_id)
            logger.error(
                "ContentStrengthAgent processing failed",
                session_id=session_id,
                processing_time_ms=round((time.time() - start_time) * 1000, 2),
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise

    def _calculate_overall_confidence(self, node: dict[str, Any]) -> float:
        """Average confidence scores across all non-empty sections."""
        arrays = ("skills", "achievements", "suggestions")
        scores = [
            self._calculate_array_average(node, key, "confidenceScore")
            for key in arrays
            if node.get(key)
        ]
        return sum(scores) / len(scores) if scores else 0.0

    def _calculate_array_average(
        self, parent: dict[str, Any], array_name: str, field_name: str
    ) -> float:
        """Return the mean of `field_name` across items in `parent[array_name]`."""
        items = parent.get(array_name)
        if not isinstance(items, list) or not items:
            return 0.0
        scores = [
            float(item[field_name])
            for item in items
            if isinstance(item, dict) and field_name in item
        ]
        return sum(scores) / len(scores) if scores else 0.0