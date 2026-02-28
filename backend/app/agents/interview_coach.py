"""Interview Coach Agent implementation."""

import os
from typing import List, Dict, Any, Optional
from .base import BaseAgent
from .gemini_service import GeminiLiveService
from .mock_config import MockConfig
from .mock_gemini_service import MockGeminiLiveService
from ..models.agent import AgentResponse
from ..models.session import SessionContext


class InterviewCoachAgent(BaseAgent):
    """Agent for providing interview coaching and simulation."""
    
    SYSTEM_PROMPT = "You are an expert Interview Coach. Provide feedback and simulation for interview preparation."
    CONFIDENCE_SCORE = 0.85
    DEFAULT_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
    
    def __init__(self, gemini_service):
        """Initialize Interview Coach Agent.
        
        Args:
            gemini_service: Gemini API service
        """
        super().__init__(
            gemini_service=gemini_service,
            system_prompt=self.SYSTEM_PROMPT,
            name="InterviewCoachAgent"
        )
        
        # Initialize appropriate service based on mock mode
        if MockConfig.is_mock_enabled():
            self.gemini_live_service = MockGeminiLiveService()
        else:
            self.gemini_live_service = GeminiLiveService()
            
            # Try to connect to Gemini Live if API key is available
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key and api_key.strip():
                try:
                    self.gemini_live_service.connect(api_key, self.DEFAULT_MODEL)
                except Exception as e:
                    print(f"Failed to connect to Gemini Live: {e}")
            else:
                print("GEMINI_API_KEY not set; Gemini Live will not be used.")
    
    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        """Process interview coaching request.
        
        Args:
            input_text: Interview question or coaching request
            context: Session context
            
        Returns:
            Agent response with interview coaching feedback
        """
        # Try to use Gemini Live first, fallback to regular Gemini
        try:
            result = self._call_gemini_live(input_text)
            if not result or result.startswith("Error"):
                # Fallback to regular Gemini
                result = self.call_gemini(input_text, context)
        except Exception:
            # Fallback to regular Gemini
            result = self.call_gemini(input_text, context)
        
        # Build decision trace for auditability
        decision_trace = [
            "InterviewCoachAgent: Generated interview coaching feedback",
            f"InterviewCoachAgent: Used coaching model with confidence {self.CONFIDENCE_SCORE}"
        ]
        
        # Add method used to trace
        if hasattr(self.gemini_live_service, 'connected') and self.gemini_live_service.connected:
            decision_trace.append("InterviewCoachAgent: Used Gemini Live for real-time response")
        else:
            decision_trace.append("InterviewCoachAgent: Used standard Gemini API (fallback)")
        
        # Create SHARP metadata
        sharp_metadata = {
            "analysis_type": "interview_coaching",
            "confidence_score": self.CONFIDENCE_SCORE,
            "gemini_live_available": getattr(self.gemini_live_service, 'connected', False)
        }
        
        return AgentResponse(
            agent_name=self.get_name(),
            content=result,
            reasoning="Generated interview coaching feedback.",
            confidence_score=self.CONFIDENCE_SCORE,
            decision_trace=decision_trace,
            sharp_metadata=sharp_metadata
        )
    
    def _call_gemini_live(self, input_text: str) -> Optional[str]:
        """Call Gemini Live service with timeout.
        
        Args:
            input_text: Input text for coaching
            
        Returns:
            Response from Gemini Live or None if error
        """
        if not hasattr(self.gemini_live_service, 'connected') or not self.gemini_live_service.connected:
            return None
        
        try:
            # Send input as text and wait for response (10s timeout)
            raw = self.gemini_live_service.send_textAndWaitResponse(input_text, 10000)
            if not raw or raw.strip() == "":
                return "(No response from Gemini Live)"
            
            # The live API returns richer messages; here we return the raw response
            return raw
        except Exception as e:
            return f"Error contacting Gemini Live: {str(e)}"
