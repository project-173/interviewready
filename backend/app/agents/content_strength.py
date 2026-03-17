"""Content Strength Agent implementation."""

import json
import re
import time
from typing import List, Dict, Any, Optional
from .base import BaseAgent
from ..core.langfuse_client import trace_agent_process
from ..core.logging import logger
from ..models.agent import AgentResponse, ContentAnalysisReport
from ..models.session import SessionContext


class ContentStrengthAgent(BaseAgent):
    """Agent for analyzing content strength, skills reasoning, and evidence evaluation."""
    
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
        
        # Log processing start
        logger.debug(f"ContentStrengthAgent processing started", 
                    session_id=session_id, 
                    input_length=len(input_text),
                    input_preview=input_text[:100] + "..." if len(input_text) > 100 else input_text)
        
        try:
            raw_result = self.call_gemini(input_text, context)
            processing_time = time.time() - processing_start_time
            
            # Log Gemini API call completion
            logger.debug(f"ContentStrengthAgent Gemini call completed", 
                        session_id=session_id, 
                        processing_time_ms=round(processing_time * 1000, 2),
                        raw_result_length=len(raw_result))
            
            parsed = self._parse_json(raw_result)
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
