"""Content Strength Agent implementation."""

import json
import time
from typing import Dict, Any

from langfuse import observe

from .base import BaseAgent
from ..core.logging import logger
from ..core.config import settings
from ..core.constants import ANTI_JAILBREAK_DIRECTIVE, RESUME_SCHEMA
from ..models.agent import AgentResponse, ContentStrengthReport, AgentInput
from ..models.session import SessionContext
from ..utils.resume_location import resume_location_exists

class ContentStrengthAgent(BaseAgent):
    """Agent for analyzing content strength, skills reasoning, and evidence evaluation."""

    USE_MOCK_RESPONSE = settings.MOCK_CONTENT_STRENGTH_AGENT
    MOCK_RESPONSE_KEY = "ContentStrengthAgent"
    
    SYSTEM_PROMPT = (
        """
        You are a Content Strength Agent. Analyze the resume and return a single JSON object, nothing else.

        FAITHFULNESS — never violate:
        - Only suggest rephrasing of text that exists verbatim in the resume
        - Never add metrics, numbers, or claims not present in the original
        - Never imply greater scope or seniority than the original supports
        - If you cannot improve a field faithfully, omit it — do not include the suggestion

        EVIDENCE STRENGTH - choose one:
        - HIGH: quantified with specific numbers, percentages, or measurable outcomes
        - MEDIUM: specific and contextual, but not quantified
        - LOW: vague or generic

        SUGGESTION TYPE (field name "type") - choose one:
        - action_verb: weak or missing opening verb (led, built, reduced, owned)
        - specificity: too vague; can be grounded using existing context
        - structure: ordering, parallelism, or run-on phrasing issues
        - redundancy: repeats information stated elsewhere

        LOCATION FORMAT: use JSON path notation matching the resume schema
        e.g. work[0].highlights[1], skills[2].keywords, projects[0].description

        OUTPUT: valid JSON only. No markdown, no text outside the object, no null values.

        {
        "suggestions": [
            {
            "location": "work[0].highlights[1]",
            "original": "exact text from resume",
            "suggested": "improved phrasing",
            "evidenceStrength": "HIGH|MEDIUM|LOW",
            "type": "action_verb|specificity|structure|redundancy"
            }
        ],
        "summary": "2-3 sentences: what this resume does well, where evidence is weakest, and the single highest-leverage improvement"
        }
        """
    + RESUME_SCHEMA
    + ANTI_JAILBREAK_DIRECTIVE
    )

    _EVIDENCE_WEIGHTS = {"HIGH": 1.0, "MEDIUM": 0.65, "LOW": 0.3}
    _SUGGESTION_RISK = {
        "action_verb": 0.0,
        "redundancy": 0.0,
        "structure": 0.05,
        "specificity": 0.2,
    }
    
    def __init__(self, gemini_service):
        """Initialize Content Strength Agent.

        Args:
            gemini_service: Gemini API service
        """
        super().__init__(
            gemini_service=gemini_service,
            system_prompt=self.SYSTEM_PROMPT,
            name="ContentStrengthAgent",
        )
    
    @observe(name="content_strength_process", as_type="agent")
    def process(
        self, input_data: AgentInput, context: SessionContext
    ) -> AgentResponse:
        """Process resume text and analyze content strength.

        Args:
            input_data: Structured agent input
            context: Session context

        Returns:
            Agent response with content strength analysis
        """
        if not isinstance(input_data, AgentInput):
            raise TypeError("ContentStrengthAgent expects AgentInput.")

        session_id = getattr(context, "session_id", "unknown")
        agent_name = self.get_name()
        processing_start_time = time.time()

        input_text = self._build_prompt(input_data)

        logger.debug(
            "ContentStrengthAgent processing started",
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

            # Ensure we have a valid dictionary for validation
            parsed = self._parse_json(raw_result) if isinstance(raw_result, str) else raw_result
            if not isinstance(parsed, dict):
                parsed = {}
            
            # Re-serialize for parse_and_validate to handle potential string output
            raw_content = json.dumps(parsed)

            structured_result = self.parse_and_validate(raw_content, ContentStrengthReport).model_dump()

            resume_payload: Dict[str, Any] = {}
            if input_data.resume is not None:
                resume_payload = input_data.resume.model_dump(exclude_none=True)

            suggestions = structured_result.get("suggestions") or []
            if resume_payload and isinstance(suggestions, list):
                valid_suggestions = [
                    suggestion
                    for suggestion in suggestions
                    if isinstance(suggestion, dict)
                    and resume_location_exists(resume_payload, suggestion.get("location", ""))
                ]
                removed = len(suggestions) - len(valid_suggestions)
                structured_result["suggestions"] = valid_suggestions
            else:
                removed = 0

            processing_time = time.time() - processing_start_time
            
            logger.debug("ContentStrengthAgent processing completed",
                        session_id=session_id,
                        processing_time_ms=round(processing_time * 1000, 2))

            overall_confidence = self._calculate_overall_confidence(structured_result)
            hallucination_risk = self._calculate_hallucination_risk(structured_result)
            summary = self._get_text_or_empty(structured_result, "summary")

            structured_result["score"] = overall_confidence
            
            decision_trace = [
                "ContentStrengthAgent: Analyzed resume for skills and achievements",
                f"ContentStrengthAgent: Identified {self._count_array(structured_result, 'skills')} skills",
                f"ContentStrengthAgent: Identified {self._count_array(structured_result, 'achievements')} achievements",
                f"ContentStrengthAgent: Generated {self._count_array(structured_result, 'suggestions')} suggestions",
                f"ContentStrengthAgent: Hallucination risk: {hallucination_risk}",
            ]

            sharp_metadata = {
                "hallucinationRisk": hallucination_risk,
                "overallConfidence": overall_confidence,
                "locationsFiltered": removed,
            }

            response = AgentResponse(
                agent_name=self.get_name(),
                content=json.dumps(structured_result, indent=2),
                reasoning=summary,
                confidence_score=overall_confidence,
                decision_trace=decision_trace,
                sharp_metadata=sharp_metadata,
            )

            # Log response creation
            logger.debug(
                "ContentStrengthAgent response created",
                session_id=session_id,
                confidence_score=overall_confidence,
                hallucination_risk=hallucination_risk,
                analysis_type="content_strength",
            )

            return response

        except Exception as e:
            processing_time = time.time() - processing_start_time
            logger.log_agent_error(agent_name, e, session_id)
            logger.error(
                "ContentStrengthAgent processing failed",
                session_id=session_id,
                processing_time_ms=round(processing_time * 1000, 2),
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise

    def _calculate_overall_confidence(self, result):
        suggestions = result.get("suggestions") or []
        if not suggestions:
            return 0

        scores = []
        for s in suggestions:
            if not isinstance(s, dict):
                continue
            ev = self._EVIDENCE_WEIGHTS.get(s.get("evidenceStrength", "LOW"), 0.3)
            type_weight = {
                "action_verb": 0.8,
                "redundancy": 0.7,
                "structure": 0.9,
                "specificity": 1.2,
            }.get(s.get("type", ""), 1.0)

            scores.append(ev * type_weight)

        if not scores:
            return 0

        avg = sum(scores) / len(scores)

        # sample size adjustment
        n = len(scores)
        size_factor = 1 - (2.71828 ** (-n / 6))

        # variance penalty
        mean = avg
        variance = sum((x - mean) ** 2 for x in scores) / len(scores)
        variance_penalty = 1 - variance

        # hallucination penalty
        hallucination_risk = self._calculate_hallucination_risk(result)
        hallucination_penalty = 1 - hallucination_risk

        confidence = avg * size_factor * variance_penalty * hallucination_penalty

        return int(max(0, min(confidence * 100, 100)))
    
    def _calculate_hallucination_risk(self, result: Dict[str, Any]) -> float:
        suggestions = result.get("suggestions") or []
        risks = [
            self._SUGGESTION_RISK.get(s.get("type", ""), 0.1)
            for s in suggestions if isinstance(s, dict)
        ]
        return round(max(risks, default=0.0), 3)

    def _calculate_array_average(
        self, parent: Dict[str, Any], array_name: str, field_name: str
    ) -> float:
        """Calculate average of a field in an array.

        Args:
            parent: Parent dictionary
            array_name: Name of the array field
            field_name: Name of the field to average

        Returns:
            Average value
        """
        if not parent.get(array_name) or not isinstance(parent[array_name], list):
            return 0.0

        total = 0.0
        count = 0

        for item in parent[array_name]:
            if isinstance(item, dict) and field_name in item:
                total += float(item[field_name])
                count += 1

        return total / count if count > 0 else 0.0

    def _count_array(self, parent: Dict[str, Any], array_name: str) -> int:
        """Count items in an array.

        Args:
            parent: Parent dictionary
            array_name: Name of the array field

        Returns:
            Number of items in array
        """
        if not parent.get(array_name) or not isinstance(parent[array_name], list):
            return 0
        return len(parent[array_name])

    def _get_text_or_empty(self, node: Dict[str, Any], field: str) -> str:
        """Get text field or return empty string.

        Args:
            node: Dictionary to get field from
            field: Field name

        Returns:
            Text value or empty string
        """
        return node.get(field, "") if isinstance(node.get(field), str) else ""

    def _get_double_or_zero(self, node: Dict[str, Any], field: str) -> float:
        """Get double field or return 0.0.

        Args:
            node: Dictionary to get field from
            field: Field name

        Returns:
            Double value or 0.0
        """
        try:
            return float(node.get(field, 0.0))
        except (ValueError, TypeError):
            return 0.0

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON from raw or fenced markdown text."""
        if not text:
            return {}

        # Remove markdown code blocks if the AI ignored instructions
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except Exception as e:
            logger.warning(f"Direct JSON parse failed, trying regex: {e}")

        # If it still fails, find the first { and last }
        try:
            start_idx = text.find("{")
            end_idx = text.rfind("}")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = text[start_idx : end_idx + 1]
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to parse JSON using regex extraction: {e}")

        return {}

    @staticmethod
    def _build_prompt(input_data: AgentInput) -> str:
        resume_data: Dict[str, Any] = {}
        if input_data.resume is not None:
            resume_data = input_data.resume.model_dump(exclude_none=True)
        return f"Resume data: {json.dumps(resume_data, indent=2)}"
