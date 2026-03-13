"""Interview Coach Agent implementation."""

import time
from typing import Optional
from .base import BaseAgent
from .gemini_service import GeminiLiveService
from ..core.config import settings
from ..core.langfuse_client import trace_agent_process, observe
from ..core.logging import logger
from ..models.agent import AgentResponse
from ..models.session import SessionContext


class InterviewCoachAgent(BaseAgent):
    """Agent for providing interview coaching and simulation."""
    USE_MOCK_RESPONSE = False
    MOCK_RESPONSE_KEY = "InterviewCoachAgent"
    
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
        
        if self.USE_MOCK_RESPONSE:
            self.gemini_live_service = None
        else:
            self.gemini_live_service = GeminiLiveService()
            
            # Try to connect to Gemini Live if API key is available
            api_key = settings.GEMINI_API_KEY
            if api_key and api_key.strip():
                try:
                    self.gemini_live_service.connect(api_key, self.DEFAULT_MODEL)
                except Exception as e:
                    print(f"Failed to connect to Gemini Live: {e}")
            else:
                print("GEMINI_API_KEY not set; Gemini Live will not be used.")
    
    @trace_agent_process
    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        """Process interview coaching request.
        
        Args:
            input_text: Interview question or coaching request
            context: Session context
            
        Returns:
            Agent response with interview coaching feedback
        """
        session_id = getattr(context, 'session_id', 'unknown')
        agent_name = self.get_name()
        processing_start_time = time.time()
        
        # Log processing start
        logger.debug(f"InterviewCoachAgent processing started", 
                    session_id=session_id, 
                    input_length=len(input_text),
                    input_preview=input_text[:100] + "..." if len(input_text) > 100 else input_text)
        
        try:
            if self.USE_MOCK_RESPONSE:
                result = self.get_mock_response_by_key(self.MOCK_RESPONSE_KEY)
                if result is None:
                    logger.warning(
                        "InterviewCoachAgent mock enabled but response key not found",
                        session_id=session_id,
                        mock_response_key=self.MOCK_RESPONSE_KEY,
                    )
                    result = self.call_gemini(input_text, context)
                    method_used = "standard_gemini_fallback"
                else:
                    method_used = "mock_response_file"
            else:
            # Try to use Gemini Live first, fallback to regular Gemini
                gemini_live_available = (
                    hasattr(self.gemini_live_service, 'connected')
                    and self.gemini_live_service.connected
                )
                logger.debug(f"InterviewCoachAgent checking Gemini Live availability", 
                            session_id=session_id, 
                            gemini_live_available=gemini_live_available)
                
                if gemini_live_available:
                    logger.debug(f"InterviewCoachAgent using Gemini Live", session_id=session_id)
                    result = self._call_gemini_live(input_text)
                    if not result or result.startswith("Error"):
                        logger.warning(f"InterviewCoachAgent Gemini Live failed, falling back to standard Gemini", 
                                     session_id=session_id, 
                                     result_preview=result[:100] if result else "No result")
                        # Fallback to regular Gemini
                        result = self.call_gemini(input_text, context)
                        method_used = "standard_gemini_fallback"
                    else:
                        method_used = "gemini_live"
                else:
                    logger.debug(f"InterviewCoachAgent using standard Gemini (Live unavailable)", session_id=session_id)
                    # Fallback to regular Gemini
                    result = self.call_gemini(input_text, context)
                    method_used = "standard_gemini"
            
            processing_time = time.time() - processing_start_time
            logger.debug(f"InterviewCoachAgent processing completed", 
                        session_id=session_id, 
                        processing_time_ms=round(processing_time * 1000, 2),
                        method_used=method_used,
                        result_length=len(result),
                        result_preview=result[:100] + "..." if len(result) > 100 else result)
            
            # Build decision trace for auditability
            decision_trace = [
                "InterviewCoachAgent: Generated interview coaching feedback",
                f"InterviewCoachAgent: Used coaching model with confidence {self.CONFIDENCE_SCORE}",
                f"InterviewCoachAgent: Method used: {method_used}"
            ]
            
            # Add method used to trace
            if method_used == "gemini_live":
                decision_trace.append("InterviewCoachAgent: Used Gemini Live for real-time response")
            elif method_used == "mock_response_file":
                decision_trace.append("InterviewCoachAgent: Used mock response from backend/mock_responses.json")
            else:
                decision_trace.append("InterviewCoachAgent: Used standard Gemini API (fallback)")
            
            # Create SHARP metadata
            sharp_metadata = {
                "analysis_type": "interview_coaching",
                "confidence_score": self.CONFIDENCE_SCORE,
                "gemini_live_available": (method_used == "gemini_live"),
                "method_used": method_used
            }
            
            response = AgentResponse(
                agent_name=self.get_name(),
                content=result,
                reasoning="Generated interview coaching feedback.",
                confidence_score=self.CONFIDENCE_SCORE,
                decision_trace=decision_trace,
                sharp_metadata=sharp_metadata
            )
            
            # Log response creation
            logger.debug(f"InterviewCoachAgent response created", 
                        session_id=session_id, 
                        confidence_score=self.CONFIDENCE_SCORE,
                        analysis_type="interview_coaching",
                        method_used=method_used)
            
            return response
            
        except Exception as e:
            processing_time = time.time() - processing_start_time
            logger.log_agent_error(agent_name, e, session_id)
            logger.error(f"InterviewCoachAgent processing failed", 
                        session_id=session_id, 
                        processing_time_ms=round(processing_time * 1000, 2),
                        error_type=type(e).__name__,
                        error_message=str(e))
            raise
    
    @observe(name="call-gemini-live", observation_type="tool")
    def _call_gemini_live(self, input_text: str) -> Optional[str]:
        """Call Gemini Live service with timeout.
        
        Args:
            input_text: Input text for coaching
            
        Returns:
            Response from Gemini Live or None if error
        """
        session_id = "unknown"  # We don't have session context here
        
        if not hasattr(self.gemini_live_service, 'connected') or not self.gemini_live_service.connected:
            logger.debug("InterviewCoachAgent Gemini Live not connected", session_id=session_id)
            return None
        
        try:
            logger.debug("InterviewCoachAgent calling Gemini Live", session_id=session_id, input_length=len(input_text))
            
            # Send input as text and wait for response (10s timeout)
            live_start_time = time.time()
            raw = self.gemini_live_service.send_textAndWaitResponse(input_text, 10000)
            live_execution_time = time.time() - live_start_time
            
            if not raw or raw.strip() == "":
                logger.warning("InterviewCoachAgent Gemini Live returned empty response", 
                             session_id=session_id, 
                             execution_time_ms=round(live_execution_time * 1000, 2))
                return "(No response from Gemini Live)"
            
            logger.debug("InterviewCoachAgent Gemini Live call successful", 
                        session_id=session_id, 
                        execution_time_ms=round(live_execution_time * 1000, 2),
                        response_length=len(raw),
                        response_preview=raw[:100] + "..." if len(raw) > 100 else raw)
            
            # The live API returns richer messages; here we return the raw response
            return raw
        except Exception as e:
            logger.log_agent_error("InterviewCoachAgent-GeminiLive", e, session_id)
            logger.error("InterviewCoachAgent Gemini Live call failed", 
                        session_id=session_id, 
                        error_type=type(e).__name__,
                        error_message=str(e))
            return f"Error contacting Gemini Live: {str(e)}"
