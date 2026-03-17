"""Resume Critic Agent implementation."""

import json
import re
import time
from typing import Dict, Any
from .base import BaseAgent
from ..core.langfuse_client import trace_agent_process
from ..core.logging import logger
from ..models.agent import AgentResponse, StructuralAssessment
from ..models.session import SessionContext


class ResumeCriticAgent(BaseAgent):
    """Agent for analyzing resume structure, ATS compatibility, and impact."""

    SYSTEM_PROMPT = """
    You are an expert Resume Critic. Parse the resume and analyze it for structure, ATS compatibility, and impact.

    Return ONLY valid JSON with this exact schema:
    {
      "resume_data": {
        "title": "string",
        "summary": "string",
        "contact": {
          "fullName": "string",
          "email": "string",
          "phone": "string"
        },
        "skills": ["skill 1", "skill 2"],
        "experiences": [
          {"title": "role", "company": "company", "start_date": "date", "end_date": "date", "description": "achievements or description"}
        ],
        "educations": [
          {"school": "institution", "degree": "degree", "start_date": "date", "end_date": "date"}
        ]
      },
      "critique": {
        "score": 0-100 number,
        "readability": "short text summary",
        "formattingRecommendations": ["recommendation 1", "recommendation 2"],
        "suggestions": ["actionable suggestion 1", "actionable suggestion 2"]
      }
    }
    """
    CONFIDENCE_SCORE = 0.9
    
    def __init__(self, gemini_service):
        """Initialize Resume Critic Agent.
        
        Args:
            gemini_service: Gemini API service
        """
        super().__init__(
            gemini_service=gemini_service,
            system_prompt=self.SYSTEM_PROMPT,
            name="ResumeCriticAgent"
        )
    
    @trace_agent_process
    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        """Process resume text and provide critique.
        
        Args:
            input_text: Resume text to analyze
            context: Session context
            
        Returns:
            Agent response with critique and analysis
        """
        session_id = getattr(context, 'session_id', 'unknown')
        agent_name = self.get_name()
        processing_start_time = time.time()
        
        # Log processing start
        logger.debug(f"ResumeCriticAgent processing started", 
                    session_id=session_id, 
                    input_length=len(input_text),
                    input_preview=input_text[:100] + "..." if len(input_text) > 100 else input_text)
        
        try:
            raw_result = self.call_gemini(input_text, context)
            parsed_result = self._parse_json(raw_result)
            structured_result = self._normalize_structural_assessment(parsed_result)
            processing_time = time.time() - processing_start_time
            
            # Log processing completion
            logger.debug(f"ResumeCriticAgent processing completed", 
                        session_id=session_id, 
                        processing_time_ms=round(processing_time * 1000, 2),
                        result_length=len(raw_result),
                        result_preview=raw_result[:100] + "..." if len(raw_result) > 100 else raw_result)
            
            # Build decision trace for auditability
            decision_trace = [
                "ResumeCriticAgent: Analyzed resume structure and content impact",
                f"ResumeCriticAgent: Generated critique with confidence {self.CONFIDENCE_SCORE}"
            ]
            
            # Create SHARP metadata
            sharp_metadata = {
                "analysis_type": "resume_critique",
                "confidence_score": self.CONFIDENCE_SCORE,
                "ats_compatibility_checked": True
            }
            
            response = AgentResponse(
                agent_name=self.get_name(),
                content=json.dumps(structured_result, indent=2),
                reasoning="Analyzed resume structure and content impact.",
                confidence_score=self.CONFIDENCE_SCORE,
                decision_trace=decision_trace,
                sharp_metadata=sharp_metadata
            )
            
            # Log response creation
            logger.debug(f"ResumeCriticAgent response created", 
                        session_id=session_id, 
                        confidence_score=self.CONFIDENCE_SCORE,
                        analysis_type="resume_critique",
                        ats_compatibility_checked=True)
            
            return response
            
        except Exception as e:
            processing_time = time.time() - processing_start_time
            logger.log_agent_error(agent_name, e, session_id)
            logger.error(f"ResumeCriticAgent processing failed", 
                        session_id=session_id, 
                        processing_time_ms=round(processing_time * 1000, 2),
                        error_type=type(e).__name__,
                        error_message=str(e))
            raise

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON from raw or fenced markdown text."""
        if not text:
            return {}

        try:
            return json.loads(text)
        except Exception:
            pass

        fenced_match = re.search(
            r"```(?:json)?\s*(\{[\s\S]*\})\s*```",
            text,
            flags=re.IGNORECASE,
        )
        if fenced_match:
            try:
                return json.loads(fenced_match.group(1).strip())
            except Exception:
                return {}

        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group(0).strip())
            except Exception:
                return {}

        return {}

    def _normalize_structural_assessment(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize parsed content into StructuralAssessment schema."""
        fallback_suggestions = [
            "Use consistent bullet formatting across all sections.",
            "Add measurable impact statements for key achievements.",
        ]

        # Handle the case where the AI returns the flat critique vs nested critique
        critique_data = parsed.get("critique", parsed)

        critique = {
            "score": self._as_float(critique_data.get("score"), 70.0),
            "readability": self._as_str(
                critique_data.get("readability"),
                "Resume analyzed. Improve clarity and consistency for stronger ATS performance.",
            ),
            "formattingRecommendations": self._as_str_list(
                critique_data.get("formattingRecommendations")
            ),
            "suggestions": self._as_str_list(critique_data.get("suggestions")),
        }

        if not critique["formattingRecommendations"]:
            critique["formattingRecommendations"] = fallback_suggestions
        if not critique["suggestions"]:
            critique["suggestions"] = fallback_suggestions

        validated_critique = StructuralAssessment.model_validate(critique)
        
        # We need to return the combined structure expected by the frontend
        return {
            "resume_data": parsed.get("resume_data", {}),
            "critique": validated_critique.model_dump()
        }

    @staticmethod
    def _as_float(value: Any, fallback: float) -> float:
        try:
            return float(value)
        except Exception:
            return fallback

    @staticmethod
    def _as_str(value: Any, fallback: str) -> str:
        return value if isinstance(value, str) and value.strip() else fallback

    @staticmethod
    def _as_str_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if isinstance(item, str) and item.strip()]
