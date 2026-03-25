"""Focused tests for InterviewCoachAgent interview-state flow."""

import json

from app.agents.gemini_service import GeminiService
from app.agents.interview_coach import InterviewCoachAgent
from app.models.agent import AgentInput
from app.models.session import SessionContext


def _build_agent(monkeypatch) -> InterviewCoachAgent:
    monkeypatch.setattr(InterviewCoachAgent, "USE_MOCK_RESPONSE", True)
    return InterviewCoachAgent(GeminiService(api_key=""))


def _build_live_agent(monkeypatch) -> InterviewCoachAgent:
    monkeypatch.setattr(InterviewCoachAgent, "USE_MOCK_RESPONSE", False)
    agent = InterviewCoachAgent(GeminiService(api_key=""))
    if getattr(agent, "gemini_live_service", None) is not None:
        agent.gemini_live_service.connected = False
    return agent


def test_interview_coach_returns_first_question_and_initializes_state(monkeypatch) -> None:
    agent = _build_agent(monkeypatch)
    context = SessionContext(session_id="s1", user_id="u1")

    response = agent.process(
        AgentInput(intent="INTERVIEW_COACH", job_description="Backend engineer role"),
        context,
    )

    payload = json.loads(response.content)
    assert payload["current_question_number"] == 1
    assert context.shared_memory["interview_active"] is True
    assert context.shared_memory["current_question_index"] == 0
    assert len(context.shared_memory["asked_questions"]) == 1


def test_interview_coach_reasks_on_low_effort_answer_without_advancing(monkeypatch) -> None:
    agent = _build_agent(monkeypatch)
    context = SessionContext(
        session_id="s2",
        user_id="u2",
        shared_memory={
            "interview_active": True,
            "current_question_index": 1,
            "asked_questions": ["Q1", "Q2"],
            "user_answers": ["answer 1"],
            "total_questions": 5,
        },
    )

    response = agent.process(
        AgentInput(
            intent="INTERVIEW_COACH",
            message_history=[{"role": "user", "text": "idk"}],
        ),
        context,
    )

    payload = json.loads(response.content)
    assert payload["can_proceed"] is False
    assert context.shared_memory["current_question_index"] == 1
    assert context.shared_memory["user_answers"] == ["answer 1"]
    assert context.shared_memory["asked_questions"] == ["Q1", "Q2"]


def test_interview_coach_rejects_greeting_answer(monkeypatch) -> None:
    agent = _build_agent(monkeypatch)
    score, feedback, can_proceed = agent._score_interview_answer(
        "Hello",
        question="Describe a challenging project you worked on.",
        context=SessionContext(job_description="Backend engineer role"),
    )

    assert score == 0.0
    assert can_proceed is False
    assert "greeting" in feedback.lower() or "answer the interview question" in feedback.lower()


def test_interview_coach_rejects_nonsense_answer(monkeypatch) -> None:
    agent = _build_agent(monkeypatch)
    score, feedback, can_proceed = agent._score_interview_answer(
        "nonsence",
        question="Tell me about a time you solved a production issue.",
        context=SessionContext(job_description="Backend engineer role"),
    )

    assert score == 0.0
    assert can_proceed is False
    assert "professional answer" in feedback.lower() or "substantive" in feedback.lower()


def test_interview_coach_uses_model_rejection_to_block_progress(monkeypatch) -> None:
    agent = _build_live_agent(monkeypatch)
    context = SessionContext(
        session_id="s-model-block",
        user_id="u-model-block",
        shared_memory={
            "interview_active": True,
            "current_question_index": 1,
            "asked_questions": ["Q1", "Q2"],
            "user_answers": ["answer 1"],
            "total_questions": 5,
        },
    )

    monkeypatch.setattr(
        agent,
        "_call_gemini_with_system_prompt",
        lambda *args, **kwargs: json.dumps(
            {
                "current_question_number": 2,
                "total_questions": 5,
                "interview_type": "technical",
                "question": "Tell me about a time when you had to learn a new technology or framework quickly. How did you approach it?",
                "keywords": ["learning", "adaptability"],
                "tip": "Be specific.",
                "feedback": "This answer is too low-effort.",
                "answer_score": 15,
                "can_proceed": False,
                "next_challenge": "Answer with a real example.",
            }
        ),
    )

    response = agent.process(
        AgentInput(
            intent="INTERVIEW_COACH",
            message_history=[{"role": "user", "text": "Hello"}],
        ),
        context,
    )

    payload = json.loads(response.content)
    assert payload["can_proceed"] is False
    assert context.shared_memory["current_question_index"] == 1
    assert context.shared_memory["user_answers"] == ["answer 1"]


def test_interview_coach_uses_model_approval_and_generates_summary(monkeypatch) -> None:
    agent = _build_live_agent(monkeypatch)
    context = SessionContext(
        session_id="s-model-pass",
        user_id="u-model-pass",
        job_description="Senior backend engineer with Python, APIs, reliability, and stakeholder communication.",
        shared_memory={
            "interview_active": True,
            "current_question_index": 4,
            "asked_questions": ["Q1", "Q2", "Q3", "Q4", "Q5"],
            "user_answers": ["a1", "a2", "a3", "a4"],
            "total_questions": 5,
        },
    )

    def _fake_model_call(_input_text, _context, system_prompt):
        if system_prompt == agent.SYSTEM_PROMPT:
            return json.dumps(
                {
                    "current_question_number": 5,
                    "total_questions": 5,
                    "interview_type": "behavioral",
                    "question": "Describe a situation where you had to collaborate with a difficult stakeholder.",
                    "keywords": ["collaboration", "communication"],
                    "tip": "Use STAR.",
                    "feedback": "Good answer with strong detail.",
                    "answer_score": 82,
                    "can_proceed": True,
                    "next_challenge": "Wrap up strongly.",
                }
            )
        return json.dumps(
            {
                "interview_complete": True,
                "summary": "Strong interview overall.",
                "strengths": ["Clear communication"],
                "areas_for_improvement": ["Add more metrics"],
                "overall_rating": "Good",
                "recommendations": ["Practice quantifying impact"],
                "final_feedback": "Keep going.",
            }
        )

    monkeypatch.setattr(agent, "_call_gemini_with_system_prompt", _fake_model_call)

    final_answer = (
        "Situation: our API latency spiked during a launch. Task: stabilize service for enterprise users. "
        "Action: I led the incident response, rolled back a risky deploy, added caching, and coordinated "
        "stakeholder updates. Result: latency dropped 60 percent and uptime recovered."
    )
    response = agent.process(
        AgentInput(
            intent="INTERVIEW_COACH",
            message_history=[{"role": "user", "text": final_answer}],
        ),
        context,
    )

    payload = json.loads(response.content)
    assert payload["interview_complete"] is True
    assert context.shared_memory["interview_active"] is False
    assert context.shared_memory["current_question_index"] == 5
    assert context.shared_memory["user_answers"][-1] == final_answer


def test_interview_coach_completes_after_final_valid_answer(monkeypatch) -> None:
    agent = _build_agent(monkeypatch)
    context = SessionContext(
        session_id="s3",
        user_id="u3",
        job_description="Senior backend engineer with Python, APIs, reliability, and stakeholder communication.",
        shared_memory={
            "interview_active": True,
            "current_question_index": 4,
            "asked_questions": ["Q1", "Q2", "Q3", "Q4", "Q5"],
            "user_answers": ["a1", "a2", "a3", "a4"],
            "total_questions": 5,
        },
    )

    final_answer = (
        "Situation: our API latency spiked during a launch. Task: stabilize service for enterprise users. "
        "Action: I led the Python incident response, rolled back a risky deploy, added caching, and coordinated "
        "stakeholder updates. Result: latency dropped 60 percent, uptime recovered, and we documented safeguards."
    )
    response = agent.process(
        AgentInput(
            intent="INTERVIEW_COACH",
            message_history=[{"role": "user", "text": final_answer}],
        ),
        context,
    )

    payload = json.loads(response.content)
    assert payload["interview_complete"] is True
    assert context.shared_memory["interview_active"] is False
    assert context.shared_memory["current_question_index"] == 5
    assert context.shared_memory["user_answers"][-1] == final_answer
