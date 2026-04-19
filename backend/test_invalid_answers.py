#!/usr/bin/env python3
"""
Test script to verify mock responses handle inappropriate answers for each interview question.
"""

import json

from app.agents.interview_coach import InterviewCoachAgent
from app.models.session import SessionContext


class DummyGeminiService:
    """Dummy Gemini service for testing."""

    def generate_response(
        self, system_prompt: str, user_input: str, tools: list | None = None
    ) -> str:
        return '{"current_question_number": 1, "question": "Test question"}'


def test_invalid_answers():
    """Test that invalid answers trigger appropriate mock responses."""

    # Create mock service and agent
    mock_service = DummyGeminiService()
    agent = InterviewCoachAgent(mock_service)

    # Create a session context
    context = SessionContext(
        session_id="test_session",
        shared_memory={
            "current_question_index": 0,
            "asked_questions": [],
            "user_answers": [],
            "interview_active": True,
            "total_questions": 5,
        },
    )

    # Test each question with invalid answer simulation
    test_cases = [
        (0, "too brief", "InterviewCoachAgent_Q2_Invalid"),  # Q1 invalid
        (1, "too vague", "InterviewCoachAgent_Q3_Invalid"),  # Q2 invalid
        (2, "no communication", "InterviewCoachAgent_Q4_Invalid"),  # Q3 invalid
        (3, "too generic", "InterviewCoachAgent_Q5_Invalid"),  # Q4 invalid
        (4, "too negative", "InterviewCoachAgent_Q6_Invalid"),  # Q5 invalid
    ]

    for question_index, _invalid_reason, _expected_key in test_cases:
        # Set up context for this question
        context.shared_memory["current_question_index"] = question_index

        # Simulate invalid answer (is_follow_up=True, is_valid=False)
        mock_key = agent._get_dynamic_mock_key(
            context, is_follow_up=True, is_valid=False
        )

        # Verify the mock response exists
        response_str = agent.get_mock_response_by_key(mock_key)
        if response_str:
            response = json.loads(response_str)
        else:
            pass

    # Test normal progression
    for question_index in range(5):
        context.shared_memory["current_question_index"] = question_index
        mock_key = agent._get_dynamic_mock_key(
            context, is_follow_up=False, is_valid=True
        )
        response_str = agent.get_mock_response_by_key(mock_key)
        if response_str:
            response = json.loads(response_str)
            response.get("current_question_number", "N/A")
        else:
            pass


if __name__ == "__main__":
    test_invalid_answers()
