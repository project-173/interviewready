"""Resume Critic Agent implementation."""

import time
from typing import List, Dict, Any
from .base import BaseAgent
from ..core.logging import logger
from ..models.agent import AgentResponse
from ..models.session import SessionContext


class ResumeCriticAgent(BaseAgent):
    """Agent for analyzing resume structure, ATS compatibility, and impact."""
    
    SYSTEM_PROMPT = "You are an expert Resume Critic. Analyze the resume for structure, ATS compatibility, and impact."
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
            # Call Gemini with the resume content
            result = self.call_gemini(input_text, context)
            processing_time = time.time() - processing_start_time
            
            # Log processing completion
            logger.debug(f"ResumeCriticAgent processing completed", 
                        session_id=session_id, 
                        processing_time_ms=round(processing_time * 1000, 2),
                        result_length=len(result),
                        result_preview=result[:100] + "..." if len(result) > 100 else result)
            
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
                content=result,
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
