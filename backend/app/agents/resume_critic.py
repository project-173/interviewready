"""Resume Critic Agent implementation."""

import json
import time
from typing import Dict, Any
from .base import BaseAgent
from langfuse import observe
from ..core.logging import logger
from ..core.config import settings
from ..models.agent import AgentResponse, StructuralAssessment
from ..models.session import SessionContext
from ..utils.json_parser import parse_json_object

class ResumeCriticAgent(BaseAgent):
    """Agent for analyzing resume structure, ATS compatibility, and impact."""
    USE_MOCK_RESPONSE = settings.MOCK_RESUME_CRITIC_AGENT
    MOCK_RESPONSE_KEY = "ResumeCriticAgent"

    SYSTEM_PROMPT = """
You are an expert Resume Critic analyzing resumes for structure, ATS compatibility, and impact.

CRITICAL OUTPUT REQUIREMENT: You MUST respond with ONLY a valid JSON object. No text before, after, or around the JSON.

RULES:
1. Your entire response must be exactly one JSON object
2. Start with '{' and end with '}' - nothing else
3. Do NOT include any markdown code blocks (no ```json or ```)
4. Do NOT include any explanatory text, preamble, or summary
5. Do NOT include comments (// or /* */)
6. Every field must be present and valid
7. String arrays must contain 2+ non-empty items
8. Score must be a number between 0-100
9. If you cannot provide data, use empty strings/arrays, never null

RESPOND WITH THIS EXACT JSON STRUCTURE AND NOTHING ELSE:
{
  "resume_data": {
    "title": "resume title",
    "summary": "professional summary",
    "contact": {
      "fullName": "full name",
      "email": "email address",
      "phone": "phone number"
    },
    "skills": ["skill 1", "skill 2", "skill 3"],
    "experiences": [
      {"title": "job title", "company": "company name", "start_date": "YYYY-MM", "end_date": "YYYY-MM", "description": "accomplishments"}
    ],
    "educations": [
      {"school": "school name", "degree": "degree type", "start_date": "YYYY-MM", "end_date": "YYYY-MM"}
    ]
  },
  "critique": {
    "score": 75,
    "readability": "assessment of resume readability",
    "formattingRecommendations": ["recommendation 1", "recommendation 2", "recommendation 3"],
    "suggestions": ["actionable suggestion 1", "actionable suggestion 2", "actionable suggestion 3"]
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
    
    @observe(name="resume_critic_process", as_type="agent")
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

            structured_result = self.parse_and_validate(raw_result, StructuralAssessment).model_dump()
            
            processing_time = time.time() - processing_start_time
            
            logger.debug("ResumeCriticAgent processing completed", 
                        session_id=session_id, 
                        processing_time_ms=round(processing_time * 1000, 2))
            
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
                content=structured_result,
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
