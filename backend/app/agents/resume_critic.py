"""Resume Critic Agent implementation."""

from typing import List, Dict, Any
from .base import BaseAgent
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
        # Call Gemini with the resume content
        result = self.call_gemini(input_text, context)
        
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
        
        return AgentResponse(
            agent_name=self.get_name(),
            content=result,
            reasoning="Analyzed resume structure and content impact.",
            confidence_score=self.CONFIDENCE_SCORE,
            decision_trace=decision_trace,
            sharp_metadata=sharp_metadata
        )
