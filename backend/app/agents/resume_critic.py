"""Resume Critic Agent implementation."""

import json
import time
from typing import Dict, Any
from .base import BaseAgent
from ..core.logging import logger
from ..models.agent import AgentResponse, StructuralAssessment
from ..models.session import SessionContext
from ..utils.json_parser import parse_json_object


class ResumeCriticAgent(BaseAgent):
    """Agent for analyzing resume structure, ATS compatibility, and impact."""
    USE_MOCK_RESPONSE = True
    MOCK_RESPONSE_KEY = "ResumeCriticAgent"

    SYSTEM_PROMPT = """
    You are an expert Resume Critic. Analyze the resume for structure, ATS compatibility, and impact.

    Return ONLY valid JSON with this exact schema:
    {
      "score": 0-100 number,
      "readability": "short text summary",
      "formattingRecommendations": ["recommendation 1", "recommendation 2"],
      "suggestions": ["actionable suggestion 1", "actionable suggestion 2"]
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
            raw_result = None
            if self.USE_MOCK_RESPONSE:
                raw_result = self.get_mock_response_by_key(self.MOCK_RESPONSE_KEY)
                if raw_result is None:
                    logger.warning(
                        "ResumeCriticAgent mock enabled but response key not found",
                        session_id=session_id,
                        mock_response_key=self.MOCK_RESPONSE_KEY,
                    )

            if raw_result is None:
                raw_result = self.call_gemini(input_text, context)
            parsed_result = parse_json_object(raw_result)
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

    def _normalize_structural_assessment(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize parsed content into StructuralAssessment schema."""
        fallback_suggestions = [
            "Use consistent bullet formatting across all sections.",
            "Add measurable impact statements for key achievements.",
        ]

        result = {
            "score": self._as_float(parsed.get("score"), 70.0),
            "readability": self._as_str(
                parsed.get("readability"),
                "Resume analyzed. Improve clarity and consistency for stronger ATS performance.",
            ),
            "formattingRecommendations": self._as_str_list(
                parsed.get("formattingRecommendations")
            ),
            "suggestions": self._as_str_list(parsed.get("suggestions")),
        }

        if not result["formattingRecommendations"]:
            result["formattingRecommendations"] = fallback_suggestions
        if not result["suggestions"]:
            result["suggestions"] = fallback_suggestions

        validated = StructuralAssessment.model_validate(result)
        return validated.model_dump()

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
