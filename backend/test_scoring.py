#!/usr/bin/env python3
"""
Test script to verify the new scoring-based validation system.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.agents.interview_coach import InterviewCoachAgent
from app.models.session import SessionContext


class DummyGeminiService:
    """Dummy Gemini service for testing."""

    def generate_response(self, system_prompt: str, user_input: str, context=None) -> str:
        return '{"current_question_number": 1, "question": "Test question"}'


def test_scoring_system():
    """Test the new scoring validation system."""

    # Create mock service and agent
    mock_service = DummyGeminiService()
    agent = InterviewCoachAgent(mock_service)

    # Create a session context
    context = SessionContext(
        session_id="test_session",
        shared_memory={
            "current_question_index": 0,
            "asked_questions": ["Describe a challenging technical problem you solved recently and how you approached it."],
            "user_answers": [],
            "interview_active": True,
            "total_questions": 5
        }
    )

    print("Testing InterviewCoachAgent scoring validation system...\n")

    # Test cases with different answer qualities
    test_cases = [
        ("I solved a complex database performance issue by optimizing queries and adding indexes.", "Good answer"),
        ("I worked on a project where we had a problem and I fixed it using my technical skills.", "Basic answer"),
        ("It was challenging. I used some tools and it worked out.", "Poor answer"),
        ("idk", "Skip answer"),
        ("I like pizza", "Irrelevant answer"),
    ]

    for answer, description in test_cases:
        score, feedback, meets_minimum = agent._score_interview_answer(answer, "Test question", context)
        print(f"{description}:")
        print(f"  Answer: '{answer}'")
        print(f"  Score: {score:.1f}/100")
        print(f"  Meets minimum: {meets_minimum}")
        print(f"  Feedback: {feedback}")
        print()

    # Test comprehensive validation
    print("Testing comprehensive validation:")
    for answer, description in test_cases[:3]:  # Skip the obviously bad ones
        can_proceed, feedback, score = agent._comprehensive_validate_answer(answer, "Test question", context, False)
        print(f"{description}:")
        print(f"  Can proceed: {can_proceed}")
        print(f"  Score: {score:.1f}/100")
        print(f"  Feedback: {feedback}")
        print()


if __name__ == "__main__":
    test_scoring_system()