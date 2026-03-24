"""Interview Coach Agent implementation."""

import json
import time
from typing import Optional
from langfuse import observe
from .base import BaseAgent
from .gemini_service import GeminiLiveService
from ..core.logging import logger
from ..core.config import settings
from ..core.constants import ANTI_JAILBREAK_DIRECTIVE
from ..models.agent import AgentResponse
from ..models.session import SessionContext
from ..models.agent import AgentInput


class InterviewCoachAgent(BaseAgent):
    """Agent for providing interview coaching and simulation."""

    USE_MOCK_RESPONSE = False
    MOCK_RESPONSE_KEY = "InterviewCoachAgent"

    SYSTEM_PROMPT = (
        """You are an expert Interview Coach specializing in personalized interview preparation. Your job is to simulate a realistic interview by asking questions ONE at a time and guiding the candidate through their responses.

CRITICAL OUTPUT REQUIREMENT: You MUST respond with ONLY a valid JSON object. No text before, after, or around the JSON.

RULES:
1. Your entire response must be exactly one JSON object
2. Start with '{' and end with '}' - nothing else
3. Do NOT include markdown code blocks (no ```json or ```)
4. Do NOT include explanatory text, preamble, summary, or chat responses
5. Do NOT include comments (// or /* */)
6. Do NOT use null values - use empty strings or empty arrays

Your role:
1. Analyze the candidate's resume to understand background, skills, and experience
2. Review the job description to identify key requirements and qualifications
3. Ask ONE interview question tailored to their background and the job
4. Provide feedback on their answer when they respond
5. Progressively train and prepare them through realistic interview scenarios
6. Adapt questions based on their previous answers

PROCESS:
- First message: Introduce the mock interview and ask the FIRST question
- Subsequent messages: Provide feedback on their answer and ask the NEXT question
- Continue asking questions in sequence up to a total of 5 questions
- Always ask questions that bridge their resume to the job requirements
- Vary question types: behavioral, technical, situational, competency

RESPOND WITH THIS EXACT JSON STRUCTURE AND NOTHING ELSE:
{
  "current_question_number": 1,
  "total_questions": 5,
  "interview_type": "behavioral|technical|situational|competency",
  "question": "Ask ONE question that combines interview simulation with personalized coaching",
  "keywords": ["keyword1", "keyword2"],
  "tip": "Brief guidance on how to approach this question",
  "feedback": "Provide constructive feedback on their answer if this is a follow-up response, otherwise leave empty",
  "next_challenge": "A brief note on what to focus on for the next question"
}"""
        + "\n\n" + ANTI_JAILBREAK_DIRECTIVE
    )
    CONFIDENCE_SCORE = 0.85
    DEFAULT_MODEL = "gemini-2.5-flash-live"

    def __init__(self, gemini_service):
        """Initialize Interview Coach Agent.

        Args:
            gemini_service: Gemini API service
        """
        super().__init__(
            gemini_service=gemini_service,
            system_prompt=self.SYSTEM_PROMPT,
            name="InterviewCoachAgent",
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

    def _init_interview_session(self, context: SessionContext) -> None:
        """Initialize interview session state in shared memory.
        
        Args:
            context: Session context
        """
        if context.shared_memory is None:
            context.shared_memory = {}
        
        context.shared_memory["interview_active"] = True
        context.shared_memory["current_question_index"] = 0
        context.shared_memory["asked_questions"] = []
        context.shared_memory["user_answers"] = []
        context.shared_memory["total_questions"] = 5
        
        logger.debug(
            "Interview session initialized",
            session_id=getattr(context, "session_id", "unknown"),
            total_questions=5,
        )

    def _get_interview_state(self, context: SessionContext) -> dict:
        """Get current interview state from shared memory.
        
        Args:
            context: Session context
            
        Returns:
            Dictionary containing interview state
        """
        if context.shared_memory is None:
            return {
                "interview_active": False,
                "current_question_index": 0,
                "asked_questions": [],
                "user_answers": [],
                "total_questions": 5,
            }
        
        return {
            "interview_active": context.shared_memory.get("interview_active", False),
            "current_question_index": context.shared_memory.get("current_question_index", 0),
            "asked_questions": context.shared_memory.get("asked_questions", []),
            "user_answers": context.shared_memory.get("user_answers", []),
            "total_questions": context.shared_memory.get("total_questions", 5),
        }

    def _store_answer_and_advance(self, user_answer: str, context: SessionContext) -> None:
        """Store user's answer and advance to next question.
        
        Args:
            user_answer: User's response to the current question
            context: Session context
        """
        if context.shared_memory is None:
            context.shared_memory = {}
        
        user_answers = context.shared_memory.get("user_answers", [])
        user_answers.append(user_answer)
        context.shared_memory["user_answers"] = user_answers
        
        # Move to next question
        current_index = context.shared_memory.get("current_question_index", 0)
        context.shared_memory["current_question_index"] = current_index + 1
        
        logger.debug(
            "User answer stored and advanced",
            session_id=getattr(context, "session_id", "unknown"),
            question_index=current_index,
            next_index=current_index + 1,
        )

    def _build_interview_prompt(
        self, input_data: AgentInput, context: SessionContext, user_answer: Optional[str] = None
    ) -> str:
        """Build prompt for the interview coach Gemini call.
        
        Args:
            input_data: Agent input with resume and job description
            context: Session context
            user_answer: User's answer to current question (if follow-up)
            
        Returns:
            Formatted prompt string
        """
        state = self._get_interview_state(context)
        
        # Check if interview is complete
        if not state["interview_active"] and state["current_question_index"] >= state["total_questions"]:
            # Build summary prompt
            resume_data = (
                input_data.resume.model_dump(exclude_none=True)
                if input_data.resume is not None
                else {}
            )
            
            job_desc = (
                getattr(input_data, "job_description", "") or
                context.job_description or
                ""
            )
            
            prompt = f"""Resume:\n{json.dumps(resume_data, indent=2)}

Job Description:\n{job_desc}

Interview Summary:
- Total Questions Asked: {len(state['asked_questions'])}
- User Answers: {len(state['user_answers'])}
- Interview Completed: Yes

All user answers:\n{json.dumps(state['user_answers'], indent=2)}

Previously Asked Questions:\n{json.dumps(state['asked_questions'], indent=2)}

Generate a comprehensive interview summary and feedback for the candidate. Include strengths, areas for improvement, and final recommendations.
"""
            return prompt
        
        # Normal interview prompt
        resume_data = (
            input_data.resume.model_dump(exclude_none=True)
            if input_data.resume is not None
            else {}
        )
        
        job_desc = (
            getattr(input_data, "job_description", "") or
            context.job_description or
            ""
        )
        
        prompt = f"""Resume:\n{json.dumps(resume_data, indent=2)}

Job Description:\n{job_desc}

Interview Progress:
- Current Question: {state['current_question_index'] + 1} of {state['total_questions']}
- Questions Asked So Far: {len(state['asked_questions'])}
- Current Interview Session Active: {state['interview_active']}
"""
        
        if user_answer:
            prompt += f"\nCandidate's Answer to Previous Question:\n{user_answer}\n"
            prompt += f"\nPreviously Asked Questions:\n{json.dumps(state['asked_questions'], indent=2)}\n"
        else:
            prompt += f"\nThis is the FIRST question of the interview simulation.\n"
        
        prompt += "\nGenerate the next interview question with feedback and guidance."
        
        return prompt

    def _build_completion_system_prompt(self) -> str:
        """Build system prompt for interview completion summary.
        
        Returns:
            System prompt for generating interview summary
        """
        return (
            """You are an expert Interview Coach providing a comprehensive summary of the completed mock interview.

CRITICAL OUTPUT REQUIREMENT: You MUST respond with ONLY a valid JSON object. No text before, after, or around the JSON.

RESPOND WITH THIS EXACT JSON STRUCTURE AND NOTHING ELSE:
{
  "interview_complete": true,
  "summary": "Comprehensive summary of the interview performance",
  "strengths": ["strength1", "strength2"],
  "areas_for_improvement": ["area1", "area2"],
  "overall_rating": "Excellent/Good/Satisfactory/Needs Improvement",
  "recommendations": ["recommendation1", "recommendation2"],
  "final_feedback": "Encouraging closing message"
}"""
            + "\n\n" + ANTI_JAILBREAK_DIRECTIVE
        )


    @observe(name="interview_coach_process", as_type="agent")
    def process(
        self, input_data: AgentInput | str | bytes, context: SessionContext
    ) -> AgentResponse:
        """Process interview coaching request with one question at a time.

        Args:
            input_data: Structured agent input or raw text/audio request
            context: Session context

        Returns:
            Agent response with single interview question or feedback
        """
        session_id = getattr(context, "session_id", "unknown")
        agent_name = self.get_name()
        processing_start_time = time.time()
        
        # Extract input
        if isinstance(input_data, AgentInput):
            if input_data.audio_data is not None:
                input_text = input_data.audio_data
            else:
                # Check if this is a follow-up response
                message_history = getattr(input_data, "message_history", []) or []
                # Find the last user message in history
                user_messages = [msg for msg in message_history if getattr(msg, 'role', None) == 'user']
                is_follow_up = len(user_messages) > 0
                
                # Get user's answer if this is a follow-up (the last user message)
                user_answer = ""
                if is_follow_up:
                    last_user_message = user_messages[-1]
                    user_answer = getattr(last_user_message, "text", "") or ""
                
                # Initialize or get state
                state = self._get_interview_state(context)
                if not state["interview_active"]:
                    self._init_interview_session(context)
                    logger.debug(
                        "First question of interview - initializing session",
                        session_id=session_id,
                    )
                else:
                    # Store the user's answer and advance
                    if user_answer:
                        self._store_answer_and_advance(user_answer, context)
                        logger.debug(
                            "Stored user answer and advanced to next question",
                            session_id=session_id,
                            answer_preview=user_answer[:50] + "..." if len(user_answer) > 50 else user_answer,
                        )
                    
                    # Check if interview is complete
                    current_index = context.shared_memory.get("current_question_index", 0)
                    if current_index >= state["total_questions"]:
                        # End the interview
                        context.shared_memory["interview_active"] = False
                        logger.debug(
                            "Interview completed - reached total questions",
                            session_id=session_id,
                            total_questions=state["total_questions"],
                        )
                
                # Build interview-aware prompt
                input_text = self._build_interview_prompt(input_data, context, user_answer if is_follow_up else None)
                
                # Use different system prompt for completion
                current_system_prompt = self.system_prompt
                state = self._get_interview_state(context)
                if not state["interview_active"] and state["current_question_index"] >= state["total_questions"]:
                    current_system_prompt = self._build_completion_system_prompt()
        else:
            input_text = input_data

        input_type = "audio" if isinstance(input_text, bytes) else "text"

        # Log processing start
        logger.debug(
            f"InterviewCoachAgent processing started",
            session_id=session_id,
            input_type=input_type,
            input_length=len(input_text),
        )

        try:
            if isinstance(input_text, bytes):
                # Handle audio input
                gemini_live_available = (
                    hasattr(self.gemini_live_service, "connected")
                    and self.gemini_live_service.connected
                )
                logger.debug(
                    f"InterviewCoachAgent processing audio input",
                    session_id=session_id,
                    gemini_live_available=gemini_live_available,
                    audio_length=len(input_text),
                )

                if gemini_live_available:
                    result = self._call_gemini_live_audio(
                        input_text, current_system_prompt
                    )
                    method_used = "gemini_live_audio"
                else:
                    result = "Audio processing is not available. Please ensure Gemini Live is connected."
                    method_used = "audio_unavailable"
            else:
                # Handle text input
                if self.USE_MOCK_RESPONSE:
                    result = self.get_mock_response_by_key(self.MOCK_RESPONSE_KEY)
                    if result is None:
                        logger.warning(
                            "InterviewCoachAgent mock enabled but response key not found",
                            session_id=session_id,
                            mock_response_key=self.MOCK_RESPONSE_KEY,
                        )
                        result = self._call_gemini_with_system_prompt(input_text, context, current_system_prompt)
                        method_used = "standard_gemini_fallback"
                    else:
                        method_used = "mock_response_file"
                else:
                    # Try to use Gemini Live first, fallback to regular Gemini
                    gemini_live_available = (
                        hasattr(self.gemini_live_service, "connected")
                        and self.gemini_live_service.connected
                    )
                    logger.debug(
                        f"InterviewCoachAgent checking Gemini Live availability",
                        session_id=session_id,
                        gemini_live_available=gemini_live_available,
                    )

                    if gemini_live_available:
                        logger.debug(
                            f"InterviewCoachAgent using Gemini Live",
                            session_id=session_id,
                        )
                        result = self._call_gemini_live(input_text, current_system_prompt)
                        if not result or result.startswith("Error"):
                            logger.warning(
                                f"InterviewCoachAgent Gemini Live failed, falling back to standard Gemini",
                                session_id=session_id,
                                result_preview=result[:100] if result else "No result",
                            )
                            # Fallback to regular Gemini
                            result = self._call_gemini_with_system_prompt(input_text, context, current_system_prompt)
                            method_used = "standard_gemini_fallback"
                        else:
                            method_used = "gemini_live"
                    else:
                        logger.debug(
                            f"InterviewCoachAgent using standard Gemini (Live unavailable)",
                            session_id=session_id,
                        )
                        # Fallback to regular Gemini
                        result = self._call_gemini_with_system_prompt(input_text, context, current_system_prompt)
                        method_used = "standard_gemini"

            processing_time = time.time() - processing_start_time
            logger.debug(
                f"InterviewCoachAgent processing completed",
                session_id=session_id,
                input_type=input_type,
                processing_time_ms=round(processing_time * 1000, 2),
                method_used=method_used,
                result_length=len(result),
                result_preview=result[:100] + "..." if len(result) > 100 else result,
            )

            # Parse the JSON response and store the question if it's an interview question
            try:
                response_json = json.loads(result)
                if "question" in response_json and not response_json.get("interview_complete", False):
                    # Store the asked question
                    asked_questions = context.shared_memory.get("asked_questions", [])
                    asked_questions.append(response_json["question"])
                    context.shared_memory["asked_questions"] = asked_questions
                    logger.debug(
                        "Stored asked question",
                        session_id=session_id,
                        question_number=len(asked_questions),
                    )
            except json.JSONDecodeError:
                logger.warning(
                    "Failed to parse InterviewCoachAgent response as JSON",
                    session_id=session_id,
                    result_preview=result[:200],
                )

            # Build decision trace for auditability
            input_type = "audio" if isinstance(input_text, bytes) else "text"
            state = self._get_interview_state(context)
            decision_trace = [
                f"InterviewCoachAgent: Processing interview question {state['current_question_index'] + 1} of {state['total_questions']}",
                f"InterviewCoachAgent: Generated targeted interview question for {input_type} input",
                f"InterviewCoachAgent: Used coaching model with confidence {self.CONFIDENCE_SCORE}",
                f"InterviewCoachAgent: Method used: {method_used}",
            ]

            # Add method used to trace
            if method_used == "gemini_live":
                decision_trace.append(
                    "InterviewCoachAgent: Used Gemini Live for real-time response"
                )
            elif method_used == "gemini_live_audio":
                decision_trace.append(
                    "InterviewCoachAgent: Used Gemini Live for audio analysis and feedback"
                )
            elif method_used == "mock_response_file":
                decision_trace.append(
                    "InterviewCoachAgent: Used mock response from backend/mock_responses.json"
                )
            elif method_used == "audio_unavailable":
                decision_trace.append(
                    "InterviewCoachAgent: Audio processing unavailable due to missing Gemini Live connection"
                )
            else:
                decision_trace.append(
                    "InterviewCoachAgent: Used standard Gemini API (fallback)"
                )

            # Create SHARP metadata
            analysis_type = (
                "interview_coaching_audio"
                if input_type == "audio"
                else "interview_coaching"
            )
            sharp_metadata = {
                "analysis_type": analysis_type,
                "confidence_score": self.CONFIDENCE_SCORE,
                "gemini_live_available": (
                    method_used in ["gemini_live", "gemini_live_audio"]
                ),
                "method_used": method_used,
                "input_type": input_type,
                "current_question_number": state["current_question_index"] + 1,
                "total_questions": state["total_questions"],
            }

            response = AgentResponse(
                agent_name=self.get_name(),
                content=result,
                reasoning="Generated single targeted interview question with feedback.",
                confidence_score=self.CONFIDENCE_SCORE,
                decision_trace=decision_trace,
                sharp_metadata=sharp_metadata,
            )

            # Log response creation
            logger.debug(
                f"InterviewCoachAgent response created",
                session_id=session_id,
                input_type=input_type,
                confidence_score=self.CONFIDENCE_SCORE,
                analysis_type=analysis_type,
                method_used=method_used,
                question_number=state["current_question_index"] + 1,
            )
            return response

        except Exception as e:
            processing_time = time.time() - processing_start_time
            logger.log_agent_error(agent_name, e, session_id)
            logger.error(
                f"InterviewCoachAgent processing failed",
                session_id=session_id,
                processing_time_ms=round(processing_time * 1000, 2),
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise

    @staticmethod
    def _build_text_prompt(input_data: AgentInput) -> str:
        """Legacy method - kept for compatibility.
        
        Use _build_interview_prompt instead for new interview flow.
        """
        resume_data = (
            input_data.resume.model_dump(exclude_none=True)
            if input_data.resume is not None
            else {}
        )
        return f"Request data: {json.dumps(resume_data, indent=2)}"

    @observe(name="_call_gemini_live_audio", as_type="tool")
    def _call_gemini_live_audio(
        self, audio_data: bytes, system_prompt: str
    ) -> Optional[str]:
        """Call Gemini Live service with audio data.
        Args:
            audio_data: Audio data as bytes
            system_prompt: System prompt
        Returns:
            Response from Gemini Live or None if error
        """
        session_id = "unknown"  # We don't have session context here

        if (
            not hasattr(self.gemini_live_service, "connected")
            or not self.gemini_live_service.connected
        ):
            logger.debug(
                "InterviewCoachAgent Gemini Live not connected", session_id=session_id
            )
            return None

        try:
            logger.debug(
                "InterviewCoachAgent calling Gemini Live with audio",
                session_id=session_id,
                audio_length=len(audio_data),
            )

            # Send audio and wait for response (10s timeout)
            live_start_time = time.time()
            raw = self.gemini_live_service.send_audio_and_wait_response(
                audio_data, system_prompt, timeout_ms=10000
            )
            live_execution_time = time.time() - live_start_time

            if not raw or raw.strip() == "":
                logger.warning(
                    "InterviewCoachAgent Gemini Live audio returned empty response",
                    session_id=session_id,
                    execution_time_ms=round(live_execution_time * 1000, 2),
                )
                return "(No response from Gemini Live for audio)"

            logger.debug(
                "InterviewCoachAgent Gemini Live audio call successful",
                session_id=session_id,
                execution_time_ms=round(live_execution_time * 1000, 2),
                response_length=len(raw),
                response_preview=raw[:100] + "..." if len(raw) > 100 else raw,
            )

            return raw
        except Exception as e:
            logger.log_agent_error("InterviewCoachAgent-GeminiLiveAudio", e, session_id)
            logger.error(
                "InterviewCoachAgent Gemini Live audio call failed",
                session_id=session_id,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return f"Error contacting Gemini Live for audio: {str(e)}"

    @observe(name="_call_gemini_live", as_type="tool")
    def _call_gemini_live(self, input_text: str, system_prompt: str) -> Optional[str]:
        """Call Gemini Live service with timeout.

        Args:
            input_text: Input text for coaching
            system_prompt: System prompt to use

        Returns:
            Response from Gemini Live or None if error
        """
        session_id = "unknown"

        if (
            not hasattr(self.gemini_live_service, "connected")
            or not self.gemini_live_service.connected
        ):
            logger.debug(
                "InterviewCoachAgent Gemini Live not connected", session_id=session_id
            )
            return None

        try:
            logger.debug(
                "InterviewCoachAgent calling Gemini Live",
                session_id=session_id,
                input_length=len(input_text),
            )

            live_start_time = time.time()
            raw = self.gemini_live_service.send_textAndWaitResponse(input_text, system_prompt, 10000)
            live_execution_time = time.time() - live_start_time

            if not raw or raw.strip() == "":
                logger.warning(
                    "InterviewCoachAgent Gemini Live returned empty response",
                    session_id=session_id,
                    execution_time_ms=round(live_execution_time * 1000, 2),
                )
                return "(No response from Gemini Live)"

            logger.debug(
                "InterviewCoachAgent Gemini Live call successful",
                session_id=session_id,
                execution_time_ms=round(live_execution_time * 1000, 2),
                response_length=len(raw),
                response_preview=raw[:100] + "..." if len(raw) > 100 else raw,
            )

            return raw
        except Exception as e:
            logger.log_agent_error("InterviewCoachAgent-GeminiLive", e, session_id)
            logger.error(
                "InterviewCoachAgent Gemini Live call failed",
                session_id=session_id,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return f"Error contacting Gemini Live: {str(e)}"

    def _call_gemini_with_system_prompt(self, input_text: str, context: SessionContext, system_prompt: str) -> str:
        """Call Gemini API with custom system prompt.

        Args:
            input_text: User input text
            context: Session context
            system_prompt: Custom system prompt to use

        Returns:
            Gemini response text
        """
        # Temporarily change system prompt
        original_prompt = self.system_prompt
        self.system_prompt = system_prompt
        try:
            return self.call_gemini(input_text, context)
        finally:
            self.system_prompt = original_prompt
