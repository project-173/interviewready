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
from ..security.llm_guard_scanner import get_llm_guard_scanner
from ..utils.json_parser import parse_json_object


class InterviewCoachAgent(BaseAgent):
    """Agent for providing interview coaching and simulation."""

    USE_MOCK_RESPONSE = settings.MOCK_INTERVIEW_COACH_AGENT
    MOCK_RESPONSE_KEY = "InterviewCoachAgent"
    SENSITIVE_PATTERNS = {
        "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
        "phone": re.compile(
            r"(?:(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4})"
        ),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    }
    BIAS_PATTERNS = {
        "age": re.compile(r"\b(young|recent graduate|digital native|energetic)\b", re.IGNORECASE),
        "gender": re.compile(r"\b(he|she|him|her|male|female|manpower)\b", re.IGNORECASE),
        "nationality": re.compile(r"\b(native english|american-born|citizens only)\b", re.IGNORECASE),
    }
    PROMPT_INJECTION_PATTERNS = [
        re.compile(r"ignore (all )?(previous|prior) instructions", re.IGNORECASE),
        re.compile(r"reveal (the )?(system prompt|hidden prompt|developer message)", re.IGNORECASE),
        re.compile(r"act as (an?|the) ", re.IGNORECASE),
        re.compile(r"jailbreak|bypass|override|disable guardrails", re.IGNORECASE),
        re.compile(r"</?(system|assistant|developer|prompt)>", re.IGNORECASE),
    ]

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
- Subsequent messages: Use the evaluator result provided in the user prompt to decide whether to proceed or re-ask
- Continue asking questions in sequence up to a total of 5 questions
- Always ask questions that bridge their resume to the job requirements
- Vary question types: behavioral, technical, situational, competency

PROGRESSION RULES:
- If the evaluator says can_proceed is true: Proceed to the next question with positive feedback
- If the evaluator says can_proceed is false: Re-ask the same question with constructive feedback
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
    EVALUATOR_SYSTEM_PROMPT = (
        """You are an expert Interview Evaluator. Your only job is to assess the candidate's latest answer to the current interview question.

CRITICAL OUTPUT REQUIREMENT: You MUST respond with ONLY a valid JSON object. No text before, after, or around the JSON.

RULES:
1. Your entire response must be exactly one JSON object
2. Start with '{' and end with '}' - nothing else
3. Do NOT include markdown code blocks
4. Do NOT include explanatory text, preamble, or summary outside JSON
5. Do NOT include comments
6. Do NOT use null values - use empty strings or empty arrays
7. answer_score must be a number from 0 to 100
8. can_proceed must be true only when the answer is relevant, substantive, and interview-ready

SCORING GUIDELINES:
- 0-30: irrelevant, adversarial, empty, or extremely low effort
- 31-60: partially relevant but weak, vague, or incomplete
- 61-80: solid and relevant answer with meaningful detail
- 81-100: strong, well-structured answer with clear impact

RESPOND WITH THIS EXACT JSON STRUCTURE AND NOTHING ELSE:
{
  "answer_score": 75,
  "can_proceed": true,
  "feedback": "Specific coaching on what was strong and what to improve."
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
        shared_memory["user_answers_redacted"] = []
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
            "user_answers_redacted": list(shared_memory.get("user_answers_redacted", [])),
            "total_questions": shared_memory.get("total_questions", 5),
        }

    def _store_answer_and_advance(self, user_answer: str, context: SessionContext) -> None:
        """Store user's answer and advance to next question."""
        shared_memory = self._ensure_shared_memory(context)
        # Ensure we don't duplicate answers if the process is called multiple times for the same state
        user_answers = list(shared_memory.get("user_answers", []))
        user_answers_redacted = list(shared_memory.get("user_answers_redacted", []))
        current_index = shared_memory.get("current_question_index", 0)

        # If we have more answers than the current index, we might be re-processing or have a race
        if len(user_answers) <= current_index:
            user_answers.append(user_answer)
            shared_memory["user_answers"] = user_answers

            sanitized_answer, _ = self._sanitize_text(user_answer)
            user_answers_redacted.append(sanitized_answer)
            shared_memory["user_answers_redacted"] = user_answers_redacted

            shared_memory["current_question_index"] = current_index + 1
            logger.debug(
                "User answer stored and advanced",
                session_id=getattr(context, "session_id", "unknown"),
                question_index=current_index,
                next_index=current_index + 1,
            )
        else:
            logger.warning(
                "User answer already stored for this index, skipping advance",
                session_id=getattr(context, "session_id", "unknown"),
                current_index=current_index,
                num_answers=len(user_answers),
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
        if not state["asked_questions"]:
            return self.MOCK_RESPONSE_KEY
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
            return "InterviewCoachAgent_Summary"
        if question_num == 1:
            return "InterviewCoachAgent"
        if question_num <= state["total_questions"]:
            return f"InterviewCoachAgent_Q{question_num}"
        return "InterviewCoachAgent_Summary"

    def _sanitize_text(self, text: str) -> tuple[str, list[str]]:
        """Redact direct identifiers before sending content to the model."""
        if not text:
            return "", []
        sanitized = text
        findings: list[str] = []
        for finding, pattern in self.SENSITIVE_PATTERNS.items():
            if pattern.search(sanitized):
                sanitized = pattern.sub(f"[REDACTED_{finding.upper()}]", sanitized)
                findings.append(finding)
        return sanitized, findings

    def _sanitize_mapping(self, value) -> tuple[object, list[str]]:
        """Redact sensitive text recursively in structured payloads."""
        findings: list[str] = []
        if isinstance(value, dict):
            sanitized_dict = {}
            for key, nested_value in value.items():
                sanitized_value, nested_findings = self._sanitize_mapping(nested_value)
                sanitized_dict[key] = sanitized_value
                findings.extend(nested_findings)
            return sanitized_dict, findings
        if isinstance(value, list):
            sanitized_list = []
            for nested_value in value:
                sanitized_value, nested_findings = self._sanitize_mapping(nested_value)
                sanitized_list.append(sanitized_value)
                findings.extend(nested_findings)
            return sanitized_list, findings
        if isinstance(value, str):
            return self._sanitize_text(value)
        return value, []

    def _detect_bias_flags(self, text: str) -> list[str]:
        """Detect potentially biased language in the hiring context."""
        if not text:
            return []
        flags: list[str] = []
        for category, pattern in self.BIAS_PATTERNS.items():
            if pattern.search(text):
                flags.append(category)
        return sorted(set(flags))

    def _detect_prompt_injection(self, text: str) -> tuple[bool, list[str]]:
        """Detect prompt-injection attempts in untrusted interview inputs."""
        if not text:
            return False, []
        findings: list[str] = []
        for pattern in self.PROMPT_INJECTION_PATTERNS:
            if pattern.search(text):
                findings.append(pattern.pattern)
        return bool(findings), findings

    def _screen_untrusted_text(self, text: str) -> tuple[bool, list[str]]:
        """Screen candidate-controlled text using heuristics plus scanner when available."""
        issues: list[str] = []
        heuristic_blocked, heuristic_findings = self._detect_prompt_injection(text)
        if heuristic_blocked:
            issues.extend(f"heuristic:{finding}" for finding in heuristic_findings)

        scanner = get_llm_guard_scanner()
        safe, _sanitized, scanner_issues = scanner.scan_input(text)
        if not safe:
            issues.extend(
                f"scanner:{issue.get('scanner', 'unknown')}"
                for issue in scanner_issues
            )
        return not issues, issues

    def _build_security_reask_response(
        self,
        state: dict,
        feedback: str,
        question: str,
        reason: str = "",
    ) -> str:
        """Return a deterministic safe re-ask when adversarial content is detected.
        
        Args:
            state: Current interview state
            feedback: User-facing feedback message
            question: The question to re-ask
            reason: Technical reason for the block (for logging/metadata, not shown to user)
        """
        response = {
            "current_question_number": min(
                state["current_question_index"] + 1,
                state["total_questions"],
            ),
            "total_questions": state["total_questions"],
            "interview_type": "behavioral",
            "question": question or "Please answer the interview question using a real work example.",
            "keywords": ["relevance", "specificity"],
            "tip": "Focus on a real example, keep it professional, and use STAR.",
            "feedback": feedback,
            "answer_score": 0,
            "can_proceed": False,
            "next_challenge": "Answer the question directly without meta-instructions or attempts to change system behavior.",
        }
        return json.dumps(response)

    def _is_service_error_response(self, text: str) -> bool:
        """Detect temporary Gemini service errors from raw model output."""
        if not text or not isinstance(text, str):
            return False

        lowered = text.lower()
        return any(
            keyword in lowered
            for keyword in (
                "error in gemini:",
                "resource_exhausted",
                "exceeded your current quota",
                "quota exceeded",
                "service unavailable",
                "temporarily unavailable",
                "429",
            )
        )

    def _build_service_error_response(
        self,
        state: dict,
        question: str,
        error_details: str = "",
    ) -> str:
        """Return a safe structured response when Gemini is unavailable."""
        response = {
            "current_question_number": min(
                state["current_question_index"] + 1,
                state["total_questions"],
            ),
            "total_questions": state["total_questions"],
            "interview_type": "behavioral",
            "question": question
            or "The interview service is temporarily unavailable. Please try again shortly.",
            "keywords": ["service", "retry"],
            "tip": "Try again in a few moments once the AI service is available.",
            "feedback": (
                "We encountered a temporary AI service issue while generating your interview coaching. "
                "Please retry in a few moments."
            ),
            "answer_score": 0,
            "can_proceed": False,
            "next_challenge": "Retry once the AI service is available.",
        }
        return json.dumps(response)

    def _build_evaluator_fallback(self, raw_result: str = "", error: Optional[Exception] = None) -> dict:
        """Return a safe fallback evaluation result when the evaluator output is invalid."""
        if error is not None:
            logger.warning(
                "Evaluator returned invalid or malformed output",
                error=str(error),
                raw_result=raw_result[:200],
            )
        else:
            logger.warning(
                "Evaluator returned invalid or malformed output",
                raw_result=raw_result[:200],
            )

        return {
            "answer_score": 0.0,
            "can_proceed": False,
            "feedback": (
                "Your response could not be evaluated because the AI evaluator returned an invalid response. "
                "This is not your fault — it\'s a technical issue on our end. Please try rephrasing your answer with more specific details about your actions and results."
            ),
        }

    def _build_interview_prompt(
        self,
        input_data: AgentInput,
        context: SessionContext,
        user_answer: str = "",
        evaluation_result: Optional[dict] = None,
    ) -> str:
        """Build prompt for the interview coach Gemini call."""
        state = self._get_interview_state(context)
        resume_data = (
            input_data.resume.model_dump(exclude_none=True)
            if input_data.resume is not None
            else {}
        )
        sanitized_resume, _ = self._sanitize_mapping(resume_data)
        job_desc = getattr(input_data, "job_description", "") or context.job_description or ""
        sanitized_job_desc, _ = self._sanitize_text(job_desc)
        sanitized_user_answer, _ = self._sanitize_text(user_answer)
        bias_flags = self._detect_bias_flags(job_desc)
        prompt = f"""Resume:\n{json.dumps(sanitized_resume, indent=2)}

Job Description:\n{sanitized_job_desc}

Interview Progress:
- Current Question: {state['current_question_index'] + 1} of {state['total_questions']}
- Questions Asked So Far: {len(state['asked_questions'])}
- Current Interview Session Active: {state['interview_active']}
"""
        if user_answer:
            prompt += f"""
Candidate's Answer to Previous Question:
{sanitized_user_answer}

Previously Asked Questions:
{json.dumps(state['asked_questions'], indent=2)}
"""
            if evaluation_result:
                prompt += f"""

Evaluator Decision:
{json.dumps(evaluation_result, indent=2)}
"""
                prompt += (
                    "\nUse the evaluator decision as authoritative. "
                    "If can_proceed is false, re-ask the same question with constructive coaching. "
                    "If can_proceed is true, move to the next question."
                )
        else:
            prompt += "\nThis is the FIRST question of the interview simulation.\n"
        prompt += (
            "\nResponsible AI rules:"
            "\n- Do not infer or mention protected attributes unless the user explicitly provides them and they are job-relevant."
            "\n- Do not reinforce biased or discriminatory job requirements."
            "\n- Keep feedback tied to evidence from the answer, resume, and job description."
            "\n- Avoid requesting or repeating direct identifiers such as email, phone number, or government ID."
        )
        if bias_flags:
            prompt += (
                "\nPotentially biased job-description signals were detected. "
                "Avoid using those signals to personalize or score the candidate."
            )
        prompt += "\nGenerate the next interview question with feedback and guidance."
        return prompt

    def _build_evaluator_prompt(
        self,
        input_data: AgentInput,
        context: SessionContext,
        user_answer: str,
    ) -> str:
        """Build prompt for the evaluator model call."""
        state = self._get_interview_state(context)
        resume_data = (
            input_data.resume.model_dump(exclude_none=True)
            if input_data.resume is not None
            else {}
        )
        sanitized_resume, _ = self._sanitize_mapping(resume_data)
        job_desc = getattr(input_data, "job_description", "") or context.job_description or ""
        sanitized_job_desc, _ = self._sanitize_text(job_desc)
        sanitized_user_answer, _ = self._sanitize_text(user_answer)
        current_question = state["asked_questions"][-1] if state["asked_questions"] else ""
        return f"""Resume:\n{json.dumps(sanitized_resume, indent=2)}

Job Description:
{sanitized_job_desc}

Current Interview Question:
{current_question}

Candidate Answer:
{sanitized_user_answer}

Evaluate only this answer. Base the score on relevance to the question, alignment to the role, specificity, structure, and evidence of impact. Do not ask a new question."""

    def _evaluate_interview_answer(
        self,
        input_data: AgentInput,
        context: SessionContext,
        user_answer: str,
    ) -> dict:
        """Evaluate the latest interview answer with an LLM-backed evaluator."""
        evaluator_prompt = self._build_evaluator_prompt(input_data, context, user_answer)
        raw_result = ""
        try:
            if self.USE_MOCK_RESPONSE:
                raw_result = self.gemini_service._generate_mock_response(
                    self.EVALUATOR_SYSTEM_PROMPT,
                    user_answer,
                )
            else:
                raw_result = self._call_gemini_with_system_prompt(
                    evaluator_prompt,
                    context,
                    self.EVALUATOR_SYSTEM_PROMPT,
                )
        except Exception as exc:
            return self._build_evaluator_fallback("", exc)

        parsed = parse_json_object(raw_result)
        if not parsed:
            return self._build_evaluator_fallback(raw_result)

        answer_score = parsed.get("answer_score")
        can_proceed = parsed.get("can_proceed")
        feedback = parsed.get("feedback")

        if not isinstance(answer_score, (int, float)):
            return self._build_evaluator_fallback(raw_result)
        if not isinstance(can_proceed, bool):
            return self._build_evaluator_fallback(raw_result)
        if not isinstance(feedback, str) or not feedback.strip():
            return self._build_evaluator_fallback(raw_result)

        return {
            "answer_score": round(float(answer_score), 2),
            "can_proceed": can_proceed,
            "feedback": feedback.strip(),
        }

    def _build_completion_prompt(self, input_data: AgentInput, context: SessionContext) -> str:
        """Build prompt for the final interview summary."""
        state = self._get_interview_state(context)
        resume_data = (
            input_data.resume.model_dump(exclude_none=True)
            if input_data.resume is not None
            else {}
        )
        sanitized_resume, _ = self._sanitize_mapping(resume_data)
        job_desc = getattr(input_data, "job_description", "") or context.job_description or ""
        sanitized_job_desc, _ = self._sanitize_text(job_desc)
        redacted_answers = state["user_answers_redacted"] or state["user_answers"]
        return f"""Resume:\n{json.dumps(sanitized_resume, indent=2)}

Job Description:\n{sanitized_job_desc}

Interview Summary:
- Total Questions Asked: {len(state['asked_questions'])}
- User Answers: {len(state['user_answers'])}
- Interview Completed: Yes

All user answers:
{json.dumps(redacted_answers, indent=2)}

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

    def _extract_follow_up(self, input_data: AgentInput) -> tuple[bool, str]:
        """Extract the latest valid user answer from message history."""
        message_history = getattr(input_data, "message_history", []) or []

        def _message_value(message, key: str) -> str:
            if isinstance(message, dict):
                value = message.get(key, "")
            else:
                value = getattr(message, key, "")
            return (value or "").strip() if isinstance(value, str) else ""

        user_messages = [
            msg
            for msg in message_history
            if _message_value(msg, "role") == "user"
            and _message_value(msg, "text")
        ]
        if not user_messages:
            return False, ""

        last_user_message = user_messages[-1]
        return True, _message_value(last_user_message, "text")

    def _build_summary_fallback_response(self) -> str:
        """Return a safe fallback summary when the summary generator output is invalid."""
        response = {
            "interview_complete": True,
            "summary": "Interview completed successfully. You provided thoughtful answers and demonstrated relevant experience.",
            "strengths": [
                "Clear communication",
                "Relevant experience",
                "Professional demeanor"
            ],
            "areas_for_improvement": [
                "Consider providing more specific examples",
                "Quantify results when possible",
                "Include more detail on your role"
            ],
            "overall_rating": "Good",
            "recommendations": [
                "Practice the STAR method for structured answers",
                "Research the company and role thoroughly",
                "Prepare specific examples of your achievements"
            ],
            "final_feedback": "Thank you for completing the mock interview. Use this feedback to continue preparing for your real interviews."
        }
        return json.dumps(response)

    def _validate_summary_response(self, response_json: dict) -> bool:
        """Validate that the summary response has the correct JSON structure.
        
        Returns True if valid, False otherwise.
        """
        required_fields = {
            "interview_complete": bool,
            "summary": str,
            "strengths": list,
            "areas_for_improvement": list,
            "overall_rating": str,
            "recommendations": list,
            "final_feedback": str,
        }

        # Check that all required fields are present
        if not isinstance(response_json, dict):
            return False

        for field, expected_type in required_fields.items():
            if field not in response_json:
                return False
            value = response_json[field]
            
            # Type checking
            if not isinstance(value, expected_type):
                return False
            
            # Additional validation for specific fields
            if field == "interview_complete" and value is not True:
                return False
            if field == "summary" and not value.strip():
                return False
            if field == "strengths" and len(value) == 0:
                return False
            if field == "areas_for_improvement" and len(value) == 0:
                return False
            if field == "overall_rating" and not value.strip():
                return False
            if field == "recommendations" and len(value) == 0:
                return False
            if field == "final_feedback" and not value.strip():
                return False
            
            # Validate array items are strings
            if field in ["strengths", "areas_for_improvement", "recommendations"]:
                if not all(isinstance(item, str) and item.strip() for item in value):
                    return False

        return True

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
        evaluation_result: Optional[dict] = None
        model_answer_score: Optional[float] = None
        model_can_proceed: Optional[bool] = None
        precomputed_result: Optional[str] = None
        method_used = "uninitialized"
        state = self._get_interview_state(context)
        security_findings: list[str] = []
        bias_flags: list[str] = []
        prompt_injection_issues: list[str] = []

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
                    is_follow_up = False
                    user_answer = ""
                else:
                    is_follow_up, user_answer = self._extract_follow_up(input_data)

                sanitized_user_answer, answer_findings = self._sanitize_text(user_answer)
                security_findings.extend(answer_findings)
                bias_flags.extend(self._detect_bias_flags(context.job_description or input_data.job_description))
                if is_follow_up and user_answer:
                    input_is_safe, prompt_injection_issues = self._screen_untrusted_text(
                        user_answer
                    )
                    if not input_is_safe:
                        reason_str = "; ".join(prompt_injection_issues) if prompt_injection_issues else "security_check_failed"
                        user_feedback = (
                            f"Your response was blocked for security reasons: {reason_str.replace('heuristic:', '').replace('scanner:', '')}. "
                            f"Please answer the interview question directly with a specific real-world example using the STAR method (Situation, Task, Action, Result)."
                        )
                        precomputed_result = self._build_security_reask_response(
                            state,
                            user_feedback,
                            state["asked_questions"][-1] if state["asked_questions"] else "",
                            reason=reason_str,
                        )
                        method_used = "security_block_reask"
                        model_answer_score = 0.0
                        model_can_proceed = False
                        input_text = self._build_interview_prompt(
                            input_data,
                            context,
                            user_answer=sanitized_user_answer,
                        )
                    else:
                        try:
                            evaluation_result = self._evaluate_interview_answer(
                                input_data,
                                context,
                                user_answer,
                            )
                            model_answer_score = evaluation_result["answer_score"]
                            model_can_proceed = evaluation_result["can_proceed"]
                        except Exception as eval_exc:
                            error_msg = str(eval_exc)
                            logger.warning(
                                "Interview evaluator failed, using safe fallback response",
                                session_id=session_id,
                                error=error_msg,
                            )
                            fallback_feedback = (
                                "Your response could not be evaluated because: The AI evaluator returned an invalid response. "
                                "This is not your fault—it's a technical issue on our end. "
                                "Please try rephrasing your answer with more specific details about your actions and results."
                            )
                            evaluation_result = {
                                "answer_score": 0.0,
                                "can_proceed": False,
                                "feedback": fallback_feedback,
                            }
                            model_answer_score = 0.0
                            model_can_proceed = False
                            method_used = "evaluator_fallback"
                        input_text = self._build_interview_prompt(
                            input_data,
                            context,
                            user_answer=user_answer,
                            evaluation_result=evaluation_result,
                        )
                else:
                    input_text = self._build_interview_prompt(
                        input_data,
                        context,
                        user_answer=user_answer,
                    )
        else:
            input_text = input_data
            if isinstance(input_data, str):
                _, security_findings = self._sanitize_text(input_data)

        input_type = "audio" if isinstance(input_text, bytes) else "text"

        # Log processing start
        logger.debug(
            f"InterviewCoachAgent processing started",
            session_id=session_id,
            input_type=input_type,
            input_length=len(input_text),
        )

        try:
            if prompt_injection_issues:
                reason_str = "; ".join(prompt_injection_issues) if prompt_injection_issues else "security_check_failed"
                user_feedback = (
                    f"Your response was blocked for security reasons: {reason_str.replace('heuristic:', '').replace('scanner:', '')}. "
                    f"Please answer the interview question directly with a specific example."
                )
                result = precomputed_result or self._build_security_reask_response(
                    state,
                    user_feedback,
                    state["asked_questions"][-1] if state["asked_questions"] else "",
                    reason=reason_str,
                )
            elif isinstance(input_text, bytes):
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
                    if not result:
                        raise RuntimeError(
                            "Gemini Live audio processing failed for InterviewCoachAgent"
                        )
                else:
                    raise RuntimeError(
                        "Audio input requires Gemini Live, but the live connection is unavailable"
                    )
            else:
                # Handle text input
                if self.USE_MOCK_RESPONSE:
                    dynamic_mock_key = self._get_dynamic_mock_key(
                        context,
                        is_follow_up,
                        model_can_proceed if model_can_proceed is not None else True,
                    )
                    result = self.get_mock_response_by_key(dynamic_mock_key)
                    if result is None:
                        logger.warning(
                            f"InterviewCoachAgent dynamic mock key not found: {dynamic_mock_key}, falling back to base key"
                        )
                        result = self.get_mock_response_by_key(self.MOCK_RESPONSE_KEY)
                        if result is None:
                            raise ValueError(
                                f"InterviewCoachAgent mock enabled but response key not found: {dynamic_mock_key} and fallback {self.MOCK_RESPONSE_KEY}"
                            )
                        method_used = "mock_response_file_fallback"
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
                        if not result:
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
            while True:
                try:
                    response_json = json.loads(result)
                    break
                except json.JSONDecodeError:
                    logger.warning(
                        "Failed to parse InterviewCoachAgent response as JSON",
                        session_id=session_id,
                        result_preview=result[:200],
                    )
                    if self._is_service_error_response(result):
                        logger.warning(
                            "InterviewCoachAgent detected Gemini service error and will return a safe service outage response",
                            session_id=session_id,
                            result_preview=result[:200],
                        )
                        result = self._build_service_error_response(
                            state,
                            state["asked_questions"][-1] if state["asked_questions"] else "",
                            result,
                        )
                        method_used = "service_error_fallback"
                        continue
                    # Fallback to a safe mock response when the model output is invalid or unsafe.
                    fallback_key = self._get_dynamic_mock_key(
                        context,
                        is_follow_up,
                        model_can_proceed if model_can_proceed is not None else True,
                    )
                    fallback_result = self.get_mock_response_by_key(fallback_key)
                    if fallback_result is None:
                        fallback_result = self.get_mock_response_by_key(self.MOCK_RESPONSE_KEY)
                    if fallback_result is None:
                        raise ValueError("InterviewCoachAgent returned non-JSON output and fallback failed")
                    logger.warning(
                        "InterviewCoachAgent using fallback mock response after invalid model output",
                        session_id=session_id,
                        fallback_key=fallback_key,
                    )
                    result = fallback_result

            if response_json.get("interview_complete", False):
                if isinstance(input_data, AgentInput) and is_follow_up and user_answer:
                    self._store_answer_and_advance(user_answer, context)
                self._set_interview_complete(context)
                state = self._get_interview_state(context)
                logger.debug(
                    "Interview completed - AI generated completion summary",
                    session_id=session_id,
                )
            elif isinstance(input_data, AgentInput):
                if is_follow_up and evaluation_result is not None:
                    response_json["answer_score"] = evaluation_result["answer_score"]
                    response_json["can_proceed"] = evaluation_result["can_proceed"]
                    response_json["feedback"] = evaluation_result["feedback"]
                    model_answer_score = evaluation_result["answer_score"]
                    model_can_proceed = evaluation_result["can_proceed"]
                    if not evaluation_result["can_proceed"] and state["asked_questions"]:
                        response_json["question"] = state["asked_questions"][-1]
                    result = json.dumps(response_json)
                else:
                    model_answer_score = response_json.get("answer_score")
                    model_can_proceed = response_json.get("can_proceed")

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
                    # Parse summary response with validation and fallback for invalid JSON/structure
                    try:
                        response_json = json.loads(result)
                        # Validate the JSON structure
                        if not self._validate_summary_response(response_json):
                            logger.warning(
                                "InterviewCoachAgent summary response has invalid structure",
                                session_id=session_id,
                                result_preview=result[:200],
                            )
                            # Use fallback summary response when structure is invalid
                            result = self._build_summary_fallback_response()
                            response_json = json.loads(result)
                            method_used = "summary_invalid_structure"
                    except json.JSONDecodeError:
                        logger.warning(
                            "Failed to parse InterviewCoachAgent summary response as JSON",
                            session_id=session_id,
                            result_preview=result[:200],
                        )
                        # Use fallback summary response when Gemini output is invalid JSON
                        result = self._build_summary_fallback_response()
                        response_json = json.loads(result)
                        method_used = "summary_fallback"
                    state = self._get_interview_state(context)

                if not response_json.get("interview_complete", False):
                    response_json["current_question_number"] = min(
                        state["current_question_index"] + 1,
                        state["total_questions"],
                    )
                    response_json["total_questions"] = state["total_questions"]

                    # Hide scoring and coaching metadata on the initial interview prompt.
                    if (
                        not is_follow_up
                        and state["current_question_index"] == 0
                        and response_json["current_question_number"] == 1
                    ):
                        for hidden_field in (
                            "tip",
                            "answer_score",
                            "can_proceed",
                            "next_challenge",
                        ):
                            response_json.pop(hidden_field, None)

                if (
                    response_json.get("question")
                    and response_json.get("current_question_number", state["current_question_index"] + 1)
                    == state["current_question_index"] + 1
                    and model_can_proceed is not False
                ):
                    self._store_question_if_new(response_json["question"], context)
                result = json.dumps(response_json)
                if state["current_question_index"] >= state["total_questions"]:
                    self._set_interview_complete(context)

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
                "InterviewCoachAgent: Scoring factors include answer relevance, job alignment, detail depth, and STAR-style structure",
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
            else:
                decision_trace.append(
                    "InterviewCoachAgent: Used standard Gemini API (fallback)"
                )
            if security_findings:
                decision_trace.append(
                    "InterviewCoachAgent: Redacted sensitive candidate data before prompt construction"
                )
            if prompt_injection_issues:
                decision_trace.append(
                    "InterviewCoachAgent: Blocked adversarial candidate input before model execution and re-asked the same question"
                )
            if bias_flags:
                decision_trace.append(
                    "InterviewCoachAgent: Detected potentially biased hiring-language signals and excluded them from coaching logic"
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
                "prompt_injection_blocked": bool(prompt_injection_issues),
                "prompt_injection_signals": prompt_injection_issues,
                "agent_security_risks": [
                    "prompt_injection_via_candidate_input",
                    "pii_exposure_in_resume_or_answers",
                    "biased_or_discriminatory_questioning",
                    "unsafe_retention_of_sensitive_interview_content",
                ],
                "security_mitigations": {
                    "code_level": [
                        "BaseAgent prompt-injection scanning before model calls",
                        "output sanitization for prompt leakage and dangerous content",
                        "PII redaction before interview prompts and completion summaries",
                    ],
                    "workflow_level": [
                        "governance audit after orchestration",
                        "human review recommendation when bias or sensitive-content signals appear",
                        "CI checks for interview security and governance tests",
                    ],
                },
                "responsible_ai": {
                    "development_alignment": [
                        "schema-constrained JSON outputs for predictable behavior",
                        "defense-in-depth scanning in the base agent",
                        "auditable decision traces and structured metadata",
                    ],
                    "deployment_alignment": [
                        "post-response governance audit",
                        "deployment workflow includes security scanning and targeted backend tests",
                        "Langfuse-compatible tracing for traceability",
                    ],
                    "explainability": {
                        "decision_basis": [
                            "resume-job alignment",
                            "question relevance",
                            "answer completeness",
                            "STAR-method structure",
                        ],
                        "user_visible_fields": [
                            "feedback",
                            "answer_score",
                            "can_proceed",
                            "next_challenge",
                        ],
                    },
                    "bias_mitigation": [
                        "do not infer protected attributes",
                        "detect biased job-description signals",
                        "focus coaching on evidence and job-relevant behavior",
                    ],
                    "sensitive_content_handling": [
                        "direct identifiers are redacted before model prompts",
                        "redacted answers are used for completion summaries",
                        "sensitive-content signals trigger governance review metadata",
                    ],
                    "governance_alignment": [
                        "SHARP metadata attached to each response",
                        "governance service can flag human review needs",
                    ],
                    "imda_model_ai_governance_framework_alignment": {
                        "internal_governance_structures_and_measures": [
                            "agent-specific risks and mitigations are attached as structured metadata",
                            "security and governance tests are enforced in CI before deployment",
                        ],
                        "human_involvement_in_ai_augmented_decision_making": [
                            "human review is recommended for sensitive or bias-related cases",
                            "agent output is advisory coaching rather than autonomous hiring action",
                        ],
                        "operations_management": [
                            "prompt-injection screening and output sanitization",
                            "PII redaction before prompts and redacted summary generation",
                            "governance audit after orchestration",
                        ],
                        "stakeholder_interaction_and_communication": [
                            "reasoning, feedback, answer_score, and can_proceed expose decision basis",
                            "decision_trace captures method path and safety interventions",
                        ],
                    },
                },
            }
            sharp_metadata["sensitive_input_detected"] = bool(security_findings)
            sharp_metadata["sensitive_input_types"] = sorted(set(security_findings))
            sharp_metadata["bias_review_required"] = bool(bias_flags)
            sharp_metadata["bias_flags"] = sorted(set(bias_flags))
            sharp_metadata["human_review_recommended"] = bool(
                security_findings or bias_flags or prompt_injection_issues
            )
            if model_answer_score is not None:
                sharp_metadata["answer_score"] = round(float(model_answer_score), 2)

            if model_can_proceed is not None:
                sharp_metadata["can_proceed"] = model_can_proceed

            response = AgentResponse(
                agent_name=self.get_name(),
                content=result,
                reasoning=(
                    "Generated interview coaching based on resume-job alignment and "
                    "answer-quality heuristics, with explainable score and progression metadata."
                ),
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
