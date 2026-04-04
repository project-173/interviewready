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

    print("Testing InterviewCoachAgent mock responses for invalid answers...\n")

    # Test each question with invalid answer simulation
    test_cases = [
        (0, "too brief", "InterviewCoachAgent_Q2_Invalid"),  # Q1 invalid
        (1, "too vague", "InterviewCoachAgent_Q3_Invalid"),  # Q2 invalid
        (2, "no communication", "InterviewCoachAgent_Q4_Invalid"),  # Q3 invalid
        (3, "too generic", "InterviewCoachAgent_Q5_Invalid"),  # Q4 invalid
        (4, "too negative", "InterviewCoachAgent_Q6_Invalid"),  # Q5 invalid
    ]

    for question_index, invalid_reason, expected_key in test_cases:
        # Set up context for this question
        context.shared_memory["current_question_index"] = question_index

        # Simulate invalid answer (is_follow_up=True, is_valid=False)
        mock_key = agent._get_dynamic_mock_key(
            context, is_follow_up=True, is_valid=False
        )
        print(
            f"Question {question_index + 1} invalid answer -> Mock key: {mock_key} (expected: {expected_key})"
        )

        # Verify the mock response exists
        response_str = agent.get_mock_response_by_key(mock_key)
        if response_str:
            response = json.loads(response_str)
            print(
                f"  ✓ Response found - Question: {response.get('question', 'N/A')[:50]}..."
            )
            print(f"  ✓ Feedback: {response.get('feedback', 'N/A')[:50]}...")
        else:
            print(f"  ✗ No response found for key: {mock_key}")

        print()

    # Test normal progression
    print("Testing normal question progression:")
    for question_index in range(5):
        context.shared_memory["current_question_index"] = question_index
        mock_key = agent._get_dynamic_mock_key(
            context, is_follow_up=False, is_valid=True
        )
        response_str = agent.get_mock_response_by_key(mock_key)
        if response_str:
            response = json.loads(response_str)
            q_num = response.get("current_question_number", "N/A")
            print(
                f"  Question {question_index + 1} -> Mock key: {mock_key}, Response Q#: {q_num}"
            )
        else:
            print(f"  ✗ No response for Question {question_index + 1}")

    print("\nTest completed!")


if __name__ == "__main__":
    test_invalid_answers()
