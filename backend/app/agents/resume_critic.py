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
    USE_MOCK_RESPONSE = False
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
        
        logger.debug("ResumeCriticAgent processing started", 
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
            
            if not raw_result or not raw_result.strip():
                raise ValueError("Empty response received from Gemini API")
            
            parsed_result = parse_json_object(raw_result)
            
            if not parsed_result:
                raise ValueError(f"Failed to parse valid JSON from Gemini response: {raw_result[:200]}...")
            
            validated_result = StructuralAssessment.model_validate(parsed_result)
            structured_result = validated_result.model_dump()
            
            if not structured_result.get("formattingRecommendations") and not structured_result.get("suggestions"):
                raise ValueError("Gemini API returned empty recommendations and suggestions")
            
            processing_time = time.time() - processing_start_time
            
            logger.debug("ResumeCriticAgent processing completed", 
                        session_id=session_id, 
                        processing_time_ms=round(processing_time * 1000, 2),
                        result_length=len(raw_result),
                        result_preview=raw_result[:100] + "..." if len(raw_result) > 100 else raw_result)
            
            decision_trace = [
                "ResumeCriticAgent: Analyzed resume structure and content impact",
                f"ResumeCriticAgent: Generated critique with confidence {self.CONFIDENCE_SCORE}"
            ]
            
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
            
            logger.debug("ResumeCriticAgent response created", 
                        session_id=session_id, 
                        confidence_score=self.CONFIDENCE_SCORE,
                        analysis_type="resume_critique",
                        ats_compatibility_checked=True)
            
            return response
            
        except Exception as e:
            processing_time = time.time() - processing_start_time
            logger.log_agent_error(agent_name, e, session_id)
            logger.error("ResumeCriticAgent processing failed", 
                        session_id=session_id, 
                        processing_time_ms=round(processing_time * 1000, 2),
                        error_type=type(e).__name__,
                        error_message=str(e))
            raise
