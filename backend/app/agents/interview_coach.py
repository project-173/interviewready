"""Interview Coach Agent implementation."""

import json
import re
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

    USE_MOCK_RESPONSE = settings.MOCK_INTERVIEW_COACH_AGENT
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
- Subsequent messages: Evaluate the candidate's answer, provide a SCORE (0-100), and decide whether to proceed or re-ask
- Continue asking questions in sequence up to a total of 5 questions
- Always ask questions that bridge their resume to the job requirements
- Vary question types: behavioral, technical, situational, competency

SCORING GUIDELINES:
- Score answers from 0-100 based on quality, relevance, and completeness
- 0-30: Completely inadequate (trolls, irrelevant, no effort)
- 31-60: Basic attempt but needs significant improvement
- 61-80: Good solid answer that meets requirements
- 81-100: Excellent answer with strong detail and structure
- Consider: relevance to job, use of specific examples, STAR method structure, length/detail
- STRICT on appropriateness: block trolls, irrelevant answers, and low-effort responses
- GENEROUS on genuine effort: allow progression for answers that show real thought

PROGRESSION RULES:
- If score >= 60: Proceed to next question with positive feedback
- If score < 60: Re-ask the same question with constructive feedback
- Always provide specific suggestions for improvement

RESPOND WITH THIS EXACT JSON STRUCTURE AND NOTHING ELSE:
{
  "current_question_number": 1,
  "total_questions": 5,
  "interview_type": "behavioral|technical|situational|competency",
  "question": "Ask ONE question that combines interview simulation with personalized coaching",
  "keywords": ["keyword1", "keyword2"],
  "tip": "Brief guidance on how to approach this question",
  "feedback": "Provide constructive feedback on their answer if this is a follow-up response, otherwise leave empty",
  "answer_score": 85,
  "can_proceed": true,
  "next_challenge": "A brief note on what to focus on for the next question"
}"""
        + "\n\n" + ANTI_JAILBREAK_DIRECTIVE
    )
    CONFIDENCE_SCORE = 0.85
    DEFAULT_MODEL = "gemini-2.5-flash"

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

    def _ensure_shared_memory(self, context: SessionContext) -> dict:
        if context.shared_memory is None:
            context.shared_memory = {}
        return context.shared_memory

    def _init_interview_session(self, context: SessionContext) -> None:
        """Initialize interview session state in shared memory."""
        shared_memory = self._ensure_shared_memory(context)
        shared_memory["interview_active"] = True
        shared_memory["current_question_index"] = 0
        shared_memory["asked_questions"] = []
        shared_memory["user_answers"] = []
        shared_memory["total_questions"] = 5
        logger.debug(
            "Interview session initialized",
            session_id=getattr(context, "session_id", "unknown"),
            total_questions=5,
        )

    def _get_interview_state(self, context: SessionContext) -> dict:
        """Get current interview state from shared memory."""
        shared_memory = self._ensure_shared_memory(context)
        return {
            "interview_active": shared_memory.get("interview_active", False),
            "current_question_index": shared_memory.get("current_question_index", 0),
            "asked_questions": list(shared_memory.get("asked_questions", [])),
            "user_answers": list(shared_memory.get("user_answers", [])),
            "total_questions": shared_memory.get("total_questions", 5),
        }

    def _store_answer_and_advance(self, user_answer: str, context: SessionContext) -> None:
        """Store user's answer and advance to next question."""
        shared_memory = self._ensure_shared_memory(context)
        user_answers = list(shared_memory.get("user_answers", []))
        user_answers.append(user_answer)
        shared_memory["user_answers"] = user_answers
        current_index = shared_memory.get("current_question_index", 0)
        shared_memory["current_question_index"] = current_index + 1
        logger.debug(
            "User answer stored and advanced",
            session_id=getattr(context, "session_id", "unknown"),
            question_index=current_index,
            next_index=current_index + 1,
        )

    def _store_question_if_new(self, question: str, context: SessionContext) -> None:
        """Store a new interview question once."""
        if not question:
            return
        shared_memory = self._ensure_shared_memory(context)
        asked_questions = list(shared_memory.get("asked_questions", []))
        if asked_questions and asked_questions[-1] == question:
            return
        asked_questions.append(question)
        shared_memory["asked_questions"] = asked_questions

    def _set_interview_complete(self, context: SessionContext) -> None:
        self._ensure_shared_memory(context)["interview_active"] = False

    def _get_dynamic_mock_key(
        self, context: SessionContext, is_follow_up: bool = False, can_proceed: bool = True
    ) -> str:
        """Get the appropriate mock response key based on interview state."""
        state = self._get_interview_state(context)
        question_num = state["current_question_index"] + 1
        if not state["interview_active"] and state["current_question_index"] >= state["total_questions"]:
            return "InterviewCoachAgent_Summary"
        if is_follow_up:
            if not can_proceed:
                invalid_keys = {
                    1: "InterviewCoachAgent_Q1_Invalid",
                    2: "InterviewCoachAgent_Q2_Invalid",
                    3: "InterviewCoachAgent_Q3_Invalid",
                    4: "InterviewCoachAgent_Q4_Invalid",
                    5: "InterviewCoachAgent_Q5_Invalid",
                }
                return invalid_keys.get(question_num, "InterviewCoachAgent_Q5_Invalid")
            if question_num < state["total_questions"]:
                return f"InterviewCoachAgent_Q{question_num + 1}"
            return "InterviewCoachAgent_Q5"
        if question_num == 1:
            return "InterviewCoachAgent"
        if question_num <= state["total_questions"]:
            return f"InterviewCoachAgent_Q{question_num}"
        return "InterviewCoachAgent_Summary"

    def _build_interview_prompt(
        self,
        input_data: AgentInput,
        context: SessionContext,
        user_answer: str = "",
    ) -> str:
        """Build prompt for the interview coach Gemini call."""
        state = self._get_interview_state(context)
        resume_data = (
            input_data.resume.model_dump(exclude_none=True)
            if input_data.resume is not None
            else {}
        )
        job_desc = getattr(input_data, "job_description", "") or context.job_description or ""
        prompt = f"""Resume:\n{json.dumps(resume_data, indent=2)}

Job Description:\n{job_desc}

Interview Progress:
- Current Question: {state['current_question_index'] + 1} of {state['total_questions']}
- Questions Asked So Far: {len(state['asked_questions'])}
- Current Interview Session Active: {state['interview_active']}
"""
        if user_answer:
            prompt += f"""
Candidate's Answer to Previous Question:
{user_answer}

Previously Asked Questions:
{json.dumps(state['asked_questions'], indent=2)}
"""
            prompt += (
                "\nEvaluate the candidate's answer yourself. If it is low-effort, irrelevant, trollish, "
                "or inappropriate, set can_proceed to false and re-ask the same question with specific coaching. "
                "If it shows genuine thought and meets the bar, set can_proceed to true and move to the next question."
            )
        else:
            prompt += "\nThis is the FIRST question of the interview simulation.\n"
        prompt += "\nGenerate the next interview question with feedback and guidance."
        return prompt

    def _build_completion_prompt(self, input_data: AgentInput, context: SessionContext) -> str:
        """Build prompt for the final interview summary."""
        state = self._get_interview_state(context)
        resume_data = (
            input_data.resume.model_dump(exclude_none=True)
            if input_data.resume is not None
            else {}
        )
        job_desc = getattr(input_data, "job_description", "") or context.job_description or ""
        return f"""Resume:\n{json.dumps(resume_data, indent=2)}

Job Description:\n{job_desc}

Interview Summary:
- Total Questions Asked: {len(state['asked_questions'])}
- User Answers: {len(state['user_answers'])}
- Interview Completed: Yes

All user answers:
{json.dumps(state['user_answers'], indent=2)}

Previously Asked Questions:
{json.dumps(state['asked_questions'], indent=2)}

Generate a comprehensive interview summary and feedback for the candidate. Include strengths, areas for improvement, and final recommendations.
"""

    def _build_completion_system_prompt(self) -> str:
        """Build system prompt for interview completion summary."""
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
            + "\n\n"
            + ANTI_JAILBREAK_DIRECTIVE
        )

    def _score_interview_answer(
        self,
        answer: str,
        question: str = "",
        context: Optional[SessionContext] = None,
    ) -> tuple[float, str, bool]:
        """Score the interview answer and decide whether to proceed."""
        if not answer or not answer.strip():
            return 0.0, "Please provide an answer to the interview question.", False
        answer = answer.strip()
        answer_lower = answer.lower()
        normalized_words = re.findall(r"[a-zA-Z']+", answer_lower)
        word_count = len(normalized_words)
        skip_indicators = [
            "idk", "i don't know", "skip", "pass", "whatever", "lol", "haha",
            "lmao", "test", "random", "don't care", "no idea", "shrug",
            "dunno", "meh", "n/a", "na", "none", "nothing", "blank", "empty",
        ]
        skip_phrases = [indicator for indicator in skip_indicators if " " in indicator or "/" in indicator or "'" in indicator]
        skip_tokens = {indicator for indicator in skip_indicators if indicator not in skip_phrases}
        if any(phrase in answer_lower for phrase in skip_phrases) or any(
            token in skip_tokens for token in normalized_words
        ):
            return 0.0, "Please provide a thoughtful answer to the interview question. Low-effort responses won't help you prepare effectively.", False
        greeting_only_indicators = {"hello", "hi", "hey", "yo", "sup", "greetings"}
        if normalized_words and all(token in greeting_only_indicators for token in normalized_words):
            return 0.0, "Please answer the interview question directly instead of sending a greeting.", False
        nonsense_indicators = {
            "nonsense", "nonsence", "asdf", "qwerty", "blah", "blahblah", "lorem",
            "ipsum", "gibberish",
        }
        if any(token in nonsense_indicators for token in normalized_words):
            return 0.0, "Please provide a professional answer that addresses the interview question.", False
        if word_count < 5:
            return 0.0, "Please provide a fuller answer with a relevant example or explanation.", False
        if len(set(normalized_words)) <= 1 and word_count <= 3:
            return 0.0, "Please provide a more substantive answer to the interview question.", False
        irrelevant_indicators = ["the weather", "my favorite color", "i like pizza", "just testing"]
        if any(phrase in answer_lower for phrase in irrelevant_indicators):
            return 0.0, "Please provide an answer that's relevant to the interview question and professional experience.", False

        score = 30.0
        feedback_parts = []
        if word_count >= 40:
            score += 25.0
        elif word_count >= 25:
            score += 20.0
        elif word_count >= 15:
            score += 15.0
            feedback_parts.append("Consider adding more specific examples or details.")
        elif word_count >= 8:
            score += 10.0
            feedback_parts.append("Your answer could benefit from more specific examples.")
        else:
            score += 5.0
            feedback_parts.append("Please provide more detail about your experience and approach.")

        answer_keywords = set(normalized_words)
        question_keywords = {
            token for token in re.findall(r"[a-zA-Z']+", (question or "").lower())
            if len(token) > 3 and token not in {"tell", "about", "when", "have", "with", "your", "this", "that"}
        }
        if question_keywords:
            overlap = len(question_keywords.intersection(answer_keywords))
            if overlap >= 2:
                score += 15.0
            elif overlap == 1:
                score += 8.0
                feedback_parts.append("Tie your answer more directly to the specific interview question.")
            else:
                feedback_parts.append("Your answer does not address the interview question clearly enough.")

        job_desc = getattr(context, "job_description", "") or "" if context else ""
        if job_desc and len(job_desc) > 50:
            job_keywords = {token for token in job_desc.lower().split() if len(token) > 3}
            overlap = len(job_keywords.intersection(answer_keywords))
            if overlap >= 3:
                score += 25.0
            elif overlap == 2:
                score += 20.0
                feedback_parts.append("Try to connect your answer more directly to the job requirements.")
            elif overlap == 1:
                score += 15.0
                feedback_parts.append("Consider how your experience relates to the specific role you're applying for.")
            else:
                score += 5.0
                feedback_parts.append("Your answer doesn't strongly connect to the job requirements.")
        else:
            score += 10.0

        star_indicators = ["situation", "task", "action", "result", "challenge", "problem", "solution", "outcome"]
        star_count = sum(1 for indicator in star_indicators if indicator in answer_lower)
        if star_count >= 3:
            score += 20.0
        elif star_count == 2:
            score += 15.0
            feedback_parts.append("Consider using the STAR method (Situation, Task, Action, Result) to structure your answer.")
        elif star_count == 1:
            score += 10.0
            feedback_parts.append("Your answer could be better structured using the STAR method.")
        else:
            score += 5.0
            feedback_parts.append("Consider structuring your answer using the STAR method for better clarity.")

        meets_minimum = score >= 60.0
        if meets_minimum:
            if score >= 90:
                feedback = "Excellent answer! You provided strong detail and clear structure."
            elif score >= 80:
                feedback = "Very good answer with solid detail and relevance."
            else:
                feedback = "Good answer that meets the requirements."
                if feedback_parts:
                    feedback += f" {feedback_parts[0]}"
        else:
            feedback = "Your answer needs improvement."
            if feedback_parts:
                feedback += f" {' '.join(feedback_parts)}"
        return score, feedback, meets_minimum

    def _extract_follow_up(self, input_data: AgentInput) -> tuple[bool, str]:
        """Extract the latest user answer from message history."""
        message_history = getattr(input_data, "message_history", []) or []
        user_messages = [msg for msg in message_history if getattr(msg, "role", None) == "user"]
        if not user_messages:
            return False, ""
        last_user_message = user_messages[-1]
        return True, (getattr(last_user_message, "text", "") or "").strip()

    def _generate_summary_response(
        self, input_data: AgentInput, context: SessionContext
    ) -> tuple[str, str]:
        """Generate the final interview summary."""
        if self.USE_MOCK_RESPONSE:
            result = self.get_mock_response_by_key("InterviewCoachAgent_Summary")
            if result is not None:
                return result, "mock_response_file"
        prompt = self._build_completion_prompt(input_data, context)
        return (
            self._call_gemini_with_system_prompt(
                prompt, context, self._build_completion_system_prompt()
            ),
            "standard_gemini",
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
        is_follow_up = False
        user_answer = ""
        fallback_score: Optional[float] = None
        fallback_feedback = ""
        fallback_can_proceed = True
        model_answer_score: Optional[float] = None
        model_can_proceed: Optional[bool] = None
        state = self._get_interview_state(context)

        # Extract input
        if isinstance(input_data, AgentInput):
            if input_data.audio_data is not None:
                input_text = input_data.audio_data
            else:
                if not state["interview_active"]:
                    self._init_interview_session(context)
                    state = self._get_interview_state(context)
                    logger.debug(
                        "First question of interview - initializing session",
                        session_id=session_id,
                    )

                is_follow_up, user_answer = self._extract_follow_up(input_data)
                if is_follow_up and self.USE_MOCK_RESPONSE:
                    fallback_score, fallback_feedback, fallback_can_proceed = self._score_interview_answer(
                        user_answer,
                        state["asked_questions"][-1] if state["asked_questions"] else "",
                        context,
                    )

                input_text = self._build_interview_prompt(
                    input_data,
                    context,
                    user_answer=user_answer,
                )
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
                        input_text, self.SYSTEM_PROMPT
                    )
                    method_used = "gemini_live_audio"
                else:
                    result = "Audio processing is not available. Please ensure Gemini Live is connected."
                    method_used = "audio_unavailable"
            else:
                # Handle text input
                if self.USE_MOCK_RESPONSE:
                    dynamic_mock_key = self._get_dynamic_mock_key(
                        context,
                        is_follow_up,
                        fallback_can_proceed,
                    )
                    result = self.get_mock_response_by_key(dynamic_mock_key)
                    if result is None:
                        logger.warning(
                            "InterviewCoachAgent mock enabled but response key not found",
                            session_id=session_id,
                            mock_response_key=dynamic_mock_key,
                        )
                        result = self._call_gemini_with_system_prompt(
                            input_text, context, self.SYSTEM_PROMPT
                        )
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
                        result = self._call_gemini_live(input_text, self.SYSTEM_PROMPT)
                        if not result or result.startswith("Error"):
                            logger.warning(
                                f"InterviewCoachAgent Gemini Live failed, falling back to standard Gemini",
                                session_id=session_id,
                                result_preview=result[:100] if result else "No result",
                            )
                            # Fallback to regular Gemini
                            result = self._call_gemini_with_system_prompt(
                                input_text, context, self.SYSTEM_PROMPT
                            )
                            method_used = "standard_gemini_fallback"
                        else:
                            method_used = "gemini_live"
                    else:
                        logger.debug(
                            f"InterviewCoachAgent using standard Gemini (Live unavailable)",
                            session_id=session_id,
                        )
                        # Fallback to regular Gemini
                        result = self._call_gemini_with_system_prompt(
                            input_text, context, self.SYSTEM_PROMPT
                        )
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

            # Parse the JSON response and handle progression logic
            try:
                response_json = json.loads(result)
                if response_json.get("interview_complete", False):
                    self._set_interview_complete(context)
                    logger.debug(
                        "Interview completed - AI generated completion summary",
                        session_id=session_id,
                    )
                elif isinstance(input_data, AgentInput):
                    model_answer_score = response_json.get("answer_score")
                    model_can_proceed = response_json.get("can_proceed")
                    if model_can_proceed is None and is_follow_up:
                        model_answer_score, fallback_feedback, fallback_can_proceed = self._score_interview_answer(
                            user_answer,
                            state["asked_questions"][-1] if state["asked_questions"] else "",
                            context,
                        )
                        model_can_proceed = fallback_can_proceed
                        if "feedback" not in response_json and fallback_feedback:
                            response_json["feedback"] = fallback_feedback
                        if "answer_score" not in response_json:
                            response_json["answer_score"] = round(model_answer_score, 2)
                        if "can_proceed" not in response_json:
                            response_json["can_proceed"] = model_can_proceed
                        result = json.dumps(response_json)

                    if is_follow_up and user_answer and model_can_proceed:
                        self._store_answer_and_advance(user_answer, context)

                    state = self._get_interview_state(context)
                    if (
                        is_follow_up
                        and user_answer
                        and model_can_proceed
                        and state["current_question_index"] >= state["total_questions"]
                    ):
                        self._set_interview_complete(context)
                        result, method_used = self._generate_summary_response(
                            input_data, context
                        )
                        response_json = json.loads(result)
                        state = self._get_interview_state(context)

                    if (
                        response_json.get("question")
                        and response_json.get("current_question_number", state["current_question_index"] + 1)
                        == state["current_question_index"] + 1
                    ):
                        self._store_question_if_new(response_json["question"], context)
                    if state["current_question_index"] >= state["total_questions"]:
                        self._set_interview_complete(context)
            except json.JSONDecodeError:
                if isinstance(input_data, AgentInput) and is_follow_up:
                    model_answer_score, fallback_feedback, fallback_can_proceed = self._score_interview_answer(
                        user_answer,
                        state["asked_questions"][-1] if state["asked_questions"] else "",
                        context,
                    )
                logger.warning(
                    "Failed to parse InterviewCoachAgent response as JSON",
                    session_id=session_id,
                    result_preview=result[:200],
                )

            # Build decision trace for auditability
            input_type = "audio" if isinstance(input_text, bytes) else "text"
            state = self._get_interview_state(context)
            current_question_number = min(
                state["current_question_index"] + 1,
                state["total_questions"],
            )
            decision_trace = [
                f"InterviewCoachAgent: Processing interview question {current_question_number} of {state['total_questions']}",
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
                "current_question_number": current_question_number,
                "total_questions": state["total_questions"],
            }
            if model_answer_score is not None:
                sharp_metadata["answer_score"] = round(float(model_answer_score), 2)
            elif fallback_score is not None:
                sharp_metadata["answer_score"] = round(fallback_score, 2)

            if model_can_proceed is not None:
                sharp_metadata["can_proceed"] = model_can_proceed
            elif is_follow_up:
                sharp_metadata["can_proceed"] = fallback_can_proceed

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
                question_number=current_question_number,
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
