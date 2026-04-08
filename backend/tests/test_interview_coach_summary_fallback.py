"""Test for InterviewCoachAgent summary response error handling and fallback."""

import json

from app.agents.gemini_service import GeminiService
from app.agents.interview_coach import InterviewCoachAgent
from app.models.agent import AgentInput
from app.models.session import SessionContext


def _build_live_agent(monkeypatch) -> InterviewCoachAgent:
    monkeypatch.setattr(InterviewCoachAgent, "USE_MOCK_RESPONSE", False)
    agent = InterviewCoachAgent(GeminiService(api_key=""))
    if getattr(agent, "gemini_live_service", None) is not None:
        agent.gemini_live_service.connected = False
    return agent


def test_interview_coach_uses_fallback_summary_when_gemini_returns_malformed_json(monkeypatch) -> None:
    """Test that summary generation gracefully falls back when Gemini returns malformed JSON."""
    agent = _build_live_agent(monkeypatch)
    context = SessionContext(
        session_id="s-summary-fallback",
        user_id="u-summary-fallback",
        job_description="Senior backend engineer with Python, APIs, and reliability.",
        shared_memory={
            "interview_active": True,
            "current_question_index": 4,
            "asked_questions": ["Q1", "Q2", "Q3", "Q4", "Q5"],
            "user_answers": ["a1", "a2", "a3", "a4"],
            "user_answers_redacted": ["a1", "a2", "a3", "a4"],
            "total_questions": 5,
        },
    )

    def _fake_model_call(_input_text, _context, system_prompt):
        # Return valid JSON for evaluator and regular responses
        if system_prompt == agent.EVALUATOR_SYSTEM_PROMPT:
            return json.dumps(
                {
                    "answer_score": 85,
                    "can_proceed": True,
                    "feedback": "Solid answer.",
                }
            )
        # Return the completion system prompt response (summary)
        if system_prompt == agent._build_completion_system_prompt():
            # Return MALFORMED JSON to trigger fallback
            return "INVALID JSON RESPONSE { missing closing brace"
        # For regular questions
        return json.dumps(
            {
                "current_question_number": 5,
                "total_questions": 5,
                "interview_type": "behavioral",
                "question": "Describe a situation where you improved reliability.",
                "keywords": ["reliability"],
                "tip": "Use STAR.",
                "feedback": "",
                "answer_score": 0,
                "can_proceed": True,
                "next_challenge": "Be specific.",
            }
        )

    monkeypatch.setattr(agent, "_call_gemini_with_system_prompt", _fake_model_call)

    final_answer = "Situation: API was down. Task: restore service. Action: I debugged and deployed a fix. Result: service recovered."
    response = agent.process(
        AgentInput(
            intent="INTERVIEW_COACH",
            message_history=[{"role": "user", "text": final_answer}],
        ),
        context,
    )

    # Verify the response is valid JSON and contains interview_complete
    payload = json.loads(response.content)
    assert payload["interview_complete"] is True
    assert payload["summary"] is not None
    assert payload["strengths"] is not None
    assert payload["areas_for_improvement"] is not None
    assert payload["overall_rating"] is not None
    assert payload["final_feedback"] is not None
    
    # Verify the interview is marked as complete
    assert context.shared_memory["interview_active"] is False
    assert context.shared_memory["current_question_index"] == 5
    assert context.shared_memory["user_answers"][-1] == final_answer


def test_interview_coach_uses_fallback_when_summary_structure_is_invalid(monkeypatch) -> None:
    """Test that summary generation falls back when Gemini returns JSON with missing required fields."""
    agent = _build_live_agent(monkeypatch)
    context = SessionContext(
        session_id="s-invalid-structure",
        user_id="u-invalid-structure",
        job_description="Backend engineer role",
        shared_memory={
            "interview_active": True,
            "current_question_index": 4,
            "asked_questions": ["Q1", "Q2", "Q3", "Q4", "Q5"],
            "user_answers": ["a1", "a2", "a3", "a4"],
            "user_answers_redacted": ["a1", "a2", "a3", "a4"],
            "total_questions": 5,
        },
    )

    def _fake_model_call(_input_text, _context, system_prompt):
        if system_prompt == agent.EVALUATOR_SYSTEM_PROMPT:
            return json.dumps({"answer_score": 85, "can_proceed": True, "feedback": "Good."})
        if system_prompt == agent._build_completion_system_prompt():
            # Return JSON with missing required fields
            return json.dumps(
                {
                    "interview_complete": True,
                    "summary": "Good interview",
                    # Missing: strengths, areas_for_improvement, overall_rating, recommendations, final_feedback
                }
            )
        return json.dumps(
            {
                "current_question_number": 5,
                "total_questions": 5,
                "interview_type": "behavioral",
                "question": "Q5",
                "keywords": ["k5"],
                "tip": "t5",
                "feedback": "",
                "answer_score": 0,
                "can_proceed": True,
                "next_challenge": "n5",
            }
        )

    monkeypatch.setattr(agent, "_call_gemini_with_system_prompt", _fake_model_call)

    response = agent.process(
        AgentInput(
            intent="INTERVIEW_COACH",
            message_history=[{"role": "user", "text": "Final answer with great details."}],
        ),
        context,
    )

    # Should fall back to valid structure
    payload = json.loads(response.content)
    assert payload["interview_complete"] is True
    assert "strengths" in payload
    assert "areas_for_improvement" in payload
    assert "overall_rating" in payload
    assert "recommendations" in payload
    assert "final_feedback" in payload
    assert isinstance(payload["strengths"], list) and len(payload["strengths"]) > 0
    assert isinstance(payload["areas_for_improvement"], list) and len(payload["areas_for_improvement"]) > 0
    assert isinstance(payload["recommendations"], list) and len(payload["recommendations"]) > 0


def test_interview_coach_uses_fallback_when_summary_field_types_are_wrong(monkeypatch) -> None:
    """Test that summary falls back when field types don't match expectations."""
    agent = _build_live_agent(monkeypatch)
    context = SessionContext(
        session_id="s-wrong-types",
        user_id="u-wrong-types",
        job_description="Backend engineer role",
        shared_memory={
            "interview_active": True,
            "current_question_index": 4,
            "asked_questions": ["Q1", "Q2", "Q3", "Q4", "Q5"],
            "user_answers": ["a1", "a2", "a3", "a4"],
            "user_answers_redacted": ["a1", "a2", "a3", "a4"],
            "total_questions": 5,
        },
    )

    def _fake_model_call(_input_text, _context, system_prompt):
        if system_prompt == agent.EVALUATOR_SYSTEM_PROMPT:
            return json.dumps({"answer_score": 85, "can_proceed": True, "feedback": "Good."})
        if system_prompt == agent._build_completion_system_prompt():
            # Return JSON with wrong field types
            return json.dumps(
                {
                    "interview_complete": True,
                    "summary": "Summary text",
                    "strengths": "should_be_an_array",  # Wrong type: string instead of list
                    "areas_for_improvement": ["area1"],
                    "overall_rating": "Good",
                    "recommendations": ["rec1"],
                    "final_feedback": "Keep going",
                }
            )
        return json.dumps(
            {
                "current_question_number": 5,
                "total_questions": 5,
                "interview_type": "behavioral",
                "question": "Q5",
                "keywords": ["k5"],
                "tip": "t5",
                "feedback": "",
                "answer_score": 0,
                "can_proceed": True,
                "next_challenge": "n5",
            }
        )

    monkeypatch.setattr(agent, "_call_gemini_with_system_prompt", _fake_model_call)

    response = agent.process(
        AgentInput(
            intent="INTERVIEW_COACH",
            message_history=[{"role": "user", "text": "Final answer."}],
        ),
        context,
    )

    # Should fall back to valid structure
    payload = json.loads(response.content)
    assert payload["interview_complete"] is True
    assert isinstance(payload["strengths"], list)
    assert isinstance(payload["areas_for_improvement"], list)
    assert isinstance(payload["recommendations"], list)


def test_interview_coach_summary_fallback_has_valid_structure(monkeypatch) -> None:
    """Test that the summary fallback response has all required fields."""
    agent = _build_live_agent(monkeypatch)
    
    # Test the fallback method directly
    fallback_response = agent._build_summary_fallback_response()
    fallback_json = json.loads(fallback_response)
    
    # Verify all required fields are present
    assert fallback_json["interview_complete"] is True
    assert isinstance(fallback_json["summary"], str)
    assert len(fallback_json["summary"]) > 0
    assert isinstance(fallback_json["strengths"], list)
    assert len(fallback_json["strengths"]) > 0
    assert isinstance(fallback_json["areas_for_improvement"], list)
    assert len(fallback_json["areas_for_improvement"]) > 0
    assert isinstance(fallback_json["overall_rating"], str)
    assert isinstance(fallback_json["recommendations"], list)
    assert len(fallback_json["recommendations"]) > 0
    assert isinstance(fallback_json["final_feedback"], str)
    assert len(fallback_json["final_feedback"]) > 0


def test_interview_coach_validate_summary_response_works_correctly(monkeypatch) -> None:
    """Test the validation method directly."""
    agent = _build_live_agent(monkeypatch)
    
    # Valid response
    valid_response = {
        "interview_complete": True,
        "summary": "Interview completed successfully.",
        "strengths": ["Communication", "Technical depth"],
        "areas_for_improvement": ["Add more examples"],
        "overall_rating": "Excellent",
        "recommendations": ["Practice more"],
        "final_feedback": "Great job!",
    }
    assert agent._validate_summary_response(valid_response) is True
    
    # Missing required field
    invalid_missing = dict(valid_response)
    del invalid_missing["strengths"]
    assert agent._validate_summary_response(invalid_missing) is False
    
    # Wrong type for field
    invalid_type = dict(valid_response)
    invalid_type["strengths"] = "should_be_list"
    assert agent._validate_summary_response(invalid_type) is False
    
    # Empty array when should have items
    invalid_empty = dict(valid_response)
    invalid_empty["strengths"] = []
    assert agent._validate_summary_response(invalid_empty) is False
    
    # Empty string when should have content
    invalid_empty_str = dict(valid_response)
    invalid_empty_str["summary"] = ""
    assert agent._validate_summary_response(invalid_empty_str) is False
    
    # Wrong value for interview_complete
    invalid_complete = dict(valid_response)
    invalid_complete["interview_complete"] = False
    assert agent._validate_summary_response(invalid_complete) is False
    
    # Array with non-string items
    invalid_array_items = dict(valid_response)
    invalid_array_items["strengths"] = [1, 2, 3]
    assert agent._validate_summary_response(invalid_array_items) is False

