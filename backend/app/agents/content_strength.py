"""Content Strength Agent implementation."""

import json
import time
from typing import Dict, Any
from .base import BaseAgent
from ..core.langfuse_client import trace_agent_process, observe
from ..core.logging import logger
from ..models.agent import AgentResponse, ContentAnalysisReport
from ..models.session import SessionContext
from ..utils.json_parser import parse_json_object

class ContentStrengthAgent(BaseAgent):
    """Agent for analyzing content strength, skills reasoning, and evidence evaluation."""
    USE_MOCK_RESPONSE = False
    MOCK_RESPONSE_KEY = "ContentStrengthAgent"
    
    SYSTEM_PROMPT = """
You are a Content Strength & Skills Reasoning Agent analyzing resumes to identify key skills, achievements, and evidence of impact.

CRITICAL OUTPUT REQUIREMENT: You MUST respond with ONLY a valid JSON object. No text before, after, or around the JSON.

RULES:
1. Your entire response must be exactly one JSON object
2. Start with '{' and end with '}' - nothing else
3. Do NOT include markdown, explanatory text, preamble, or summary
4. Do NOT include comments (// or /* */)
5. All array fields must have 2+ items minimum
6. All scores must be numbers 0-1.0 (not percentages)
7. Do NOT use null - use empty strings/arrays/0

Your Responsibilities:
1. Identify key skills and achievements from the resume
2. Evaluate the strength of evidence supporting each claim
3. Suggest stronger phrasing WITHOUT fabricating new content
4. Apply confidence scoring and consistency checks

Evidence Strength: HIGH (quantified results) | MEDIUM (specific but not quantified) | LOW (vague claims)

Faithful Transformation Rules:
- NEVER invent new skills, achievements, or experiences
- NEVER add numbers or metrics that don't exist
- ONLY suggest phrasing that preserves original meaning
- If suggestion requires fabrication, mark faithful=false

RESPOND WITH THIS EXACT JSON STRUCTURE AND NOTHING ELSE:
{
  "skills": [
    {"name": "skill name", "category": "Technical|Soft|Domain|Tool", "confidenceScore": 0.85, "evidenceStrength": "HIGH|MEDIUM|LOW", "evidence": "quote from resume"}
  ],
  "achievements": [
    {"description": "achievement", "impact": "HIGH|MEDIUM|LOW", "quantifiable": true, "confidenceScore": 0.9, "originalText": "original text"}
  ],
  "suggestions": [
    {"original": "original phrasing", "suggested": "improved phrasing", "rationale": "why this helps", "faithful": true, "confidenceScore": 0.8}
  ],
  "hallucinationRisk": 0.15,
  "summary": "brief summary of analysis"
}
"""
    
    def __init__(self, gemini_service):
        """Initialize Content Strength Agent.
        
        Args:
            gemini_service: Gemini API service
        """
        super().__init__(
            gemini_service=gemini_service,
            system_prompt=self.SYSTEM_PROMPT,
            name="ContentStrengthAgent"
        )
    
    @trace_agent_process
    @observe(name="content_strength_process", observation_type="agent")
    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        """Process resume text and analyze content strength.
        
        Args:
            input_text: Resume text to analyze
            context: Session context
            
        Returns:
            Agent response with content strength analysis
        """
        session_id = getattr(context, 'session_id', 'unknown')
        agent_name = self.get_name()
        processing_start_time = time.time()
        
        logger.debug("ContentStrengthAgent processing started", 
                    session_id=session_id, 
                    input_length=len(input_text),
                    input_preview=input_text[:100] + "..." if len(input_text) > 100 else input_text)
        
        try:
            raw_result = None
            if self.USE_MOCK_RESPONSE:
                raw_result = self.get_mock_response_by_key(self.MOCK_RESPONSE_KEY)
                if raw_result is None:
                    logger.warning(
                        "ContentStrengthAgent mock enabled but response key not found",
                        session_id=session_id,
                        mock_response_key=self.MOCK_RESPONSE_KEY,
                    )

            if raw_result is None:
                raw_result = self.call_gemini(input_text, context)
            
            # Validate that we got a meaningful response
            if not raw_result or not raw_result.strip():
                raise ValueError("Empty response received from Gemini API")
            
            processing_time = time.time() - processing_start_time
            
            logger.debug("ContentStrengthAgent processing completed", 
                        session_id=session_id, 
                        processing_time_ms=round(processing_time * 1000, 2),
                        result_length=len(raw_result),
                        result_preview=raw_result[:100] + "..." if len(raw_result) > 100 else raw_result)
            
            parsed = parse_json_object(raw_result)

            # Validate that parsing succeeded
            if not parsed:
                raise ValueError(f"Failed to parse valid JSON from Gemini response: {raw_result[:200]}...")

            if parsed:
                logger.debug("ContentStrengthAgent JSON parsing successful",
                            session_id=session_id, keys_found=list(parsed.keys()))
            else:
                logger.warning("ContentStrengthAgent JSON parsing failed",
                            session_id=session_id, text_preview=raw_result[:200])
                
            normalized = self._normalize_content_analysis(parsed)
            
            # Log parsing results
            logger.debug(f"ContentStrengthAgent JSON parsing completed", 
                        session_id=session_id, 
                        parsing_successful=bool(parsed),
                        parsed_keys=list(parsed.keys()) if parsed else [])
            
            overall_confidence = self._calculate_overall_confidence(normalized)
            hallucination_risk = self._get_double_or_zero(normalized, "hallucinationRisk")
            summary = self._get_text_or_empty(normalized, "summary")
            
            # Log analysis metrics
            logger.debug(f"ContentStrengthAgent analysis metrics calculated", 
                        session_id=session_id, 
                        overall_confidence=overall_confidence,
                        hallucination_risk=hallucination_risk,
                        skills_count=self._count_array(normalized, 'skills'),
                        achievements_count=self._count_array(normalized, 'achievements'),
                        suggestions_count=self._count_array(normalized, 'suggestions'))
            
            decision_trace = [
                "ContentStrengthAgent: Analyzed resume for skills and achievements",
                f"ContentStrengthAgent: Identified {self._count_array(normalized, 'skills')} skills",
                f"ContentStrengthAgent: Identified {self._count_array(normalized, 'achievements')} achievements",
                f"ContentStrengthAgent: Generated {self._count_array(normalized, 'suggestions')} suggestions",
                f"ContentStrengthAgent: Hallucination risk: {hallucination_risk}"
            ]
            
            sharp_metadata = {
                "hallucinationRisk": hallucination_risk,
                "overallConfidence": overall_confidence
            }
            
            response = AgentResponse(
                agent_name=self.get_name(),
                content=json.dumps(normalized, indent=2),
                reasoning=summary,
                confidence_score=overall_confidence,
                decision_trace=decision_trace,
                sharp_metadata=sharp_metadata
            )
            
            # Log response creation
            logger.debug(f"ContentStrengthAgent response created", 
                        session_id=session_id, 
                        confidence_score=overall_confidence,
                        hallucination_risk=hallucination_risk,
                        analysis_type="content_strength")
            
            return response
            
        except Exception as e:
            processing_time = time.time() - processing_start_time
            logger.log_agent_error(agent_name, e, session_id)
            logger.error(f"ContentStrengthAgent processing failed", 
                        session_id=session_id, 
                        processing_time_ms=round(processing_time * 1000, 2),
                        error_type=type(e).__name__,
                        error_message=str(e))
            raise
    
    @observe(name="parse-json", observation_type="tool")
    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON from text with regex fallback.
        
        Args:
            text: Text containing JSON
            
        Returns:
            Parsed JSON dictionary
        """
        session_id = "unknown"  # We don't have session context here
        
        try:
            json_pattern = re.compile(r'\{[\s\S]*\}', re.MULTILINE)
            matcher = json_pattern.search(text)
            if matcher:
                result = json.loads(matcher.group())
                logger.debug("JSON parsing successful with regex", session_id=session_id, keys_found=list(result.keys()))
                return result
            
            result = json.loads(text)
            logger.debug("JSON parsing successful without regex", session_id=session_id, keys_found=list(result.keys()))
            return result
        except Exception as e:
            logger.warning("JSON parsing failed, returning empty dict", session_id=session_id, error=str(e), text_preview=text[:200])
            return {}
    
    def _calculate_overall_confidence(self, node: Dict[str, Any]) -> float:
        """Calculate overall confidence from parsed data.
        
        Args:
            node: Parsed JSON data
            
        Returns:
            Overall confidence score
        """
        skill_avg = self._calculate_array_average(node, "skills", "confidenceScore")
        achievement_avg = self._calculate_array_average(node, "achievements", "confidenceScore")
        suggestion_avg = self._calculate_array_average(node, "suggestions", "confidenceScore")
        
        count = 0
        total = 0.0

        if node.get("skills") and isinstance(node["skills"], list) and len(node["skills"]) > 0:
            total += skill_avg
            count += 1
        if node.get("achievements") and isinstance(node["achievements"], list) and len(node["achievements"]) > 0:
            total += achievement_avg
            count += 1
        if node.get("suggestions") and isinstance(node["suggestions"], list) and len(node["suggestions"]) > 0:
            total += suggestion_avg
            count += 1
        
        return total / count if count > 0 else 0.0
    
    def _calculate_array_average(self, parent: Dict[str, Any], array_name: str, field_name: str) -> float:
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

    @observe(name="normalize-content-analysis", observation_type="tool")
    def _normalize_content_analysis(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize parsed JSON to match ContentAnalysisReport model."""
        data: Dict[str, Any] = {
            "skills": parsed.get("skills", []),
            "achievements": parsed.get("achievements", []),
            "suggestions": parsed.get("suggestions", []),
            "hallucinationRisk": self._get_double_or_zero(parsed, "hallucinationRisk"),
            "summary": self._get_text_or_empty(parsed, "summary"),
        }
        try:
            validated = ContentAnalysisReport.model_validate(data)
            return validated.model_dump()
        except Exception:
            fallback = ContentAnalysisReport(
                skills=[],
                achievements=[],
                suggestions=[],
                hallucinationRisk=self._get_double_or_zero(parsed, "hallucinationRisk"),
                summary=self._get_text_or_empty(parsed, "summary"),
            )
            return fallback.model_dump()
