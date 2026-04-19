#!/usr/bin/env python3
"""Quick test script for per-agent inline mock responses."""

import json
import sys
from pathlib import Path

from app.agents.content_strength import ContentStrengthAgent
from app.agents.interview_coach import InterviewCoachAgent
from app.agents.job_alignment import JobAlignmentAgent
from app.agents.resume_critic import ResumeCriticAgent
from app.models import AgentInput, Resume, Work
from app.models.session import SessionContext

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


class DummyGeminiService:
    """Fallback Gemini service for tests."""

    def generate_response(
        self, system_prompt: str, user_input: str, tools: list | None = None
    ) -> str:
        if "Resume Critic" in system_prompt:
            return json.dumps(
                {
                    "score": 70,
                    "readability": "fallback",
                    "formattingRecommendations": ["fallback"],
                    "suggestions": ["fallback"],
                }
            )
        if "Content Strength" in system_prompt:
            return json.dumps(
                {
                    "skills": [],
                    "achievements": [],
                    "suggestions": [],
                    "hallucinationRisk": 0.0,
                    "summary": "fallback",
                }
            )
        if "Job Description Alignment Agent" in system_prompt:
            return json.dumps(
                {
                    "skillsMatch": [],
                    "missingSkills": [],
                    "experienceMatch": "fallback",
                    "fitScore": 50,
                    "reasoning": "fallback",
                }
            )
        return "fallback"


def test_agents_with_inline_mock() -> bool:
    original_flags = {
        ResumeCriticAgent: ResumeCriticAgent.USE_MOCK_RESPONSE,
        ContentStrengthAgent: ContentStrengthAgent.USE_MOCK_RESPONSE,
        JobAlignmentAgent: JobAlignmentAgent.USE_MOCK_RESPONSE,
        InterviewCoachAgent: InterviewCoachAgent.USE_MOCK_RESPONSE,
    }

    try:
        for agent_cls in original_flags:
            agent_cls.USE_MOCK_RESPONSE = True

        gemini = DummyGeminiService()
        agents = [
            ContentStrengthAgent(gemini),
            ResumeCriticAgent(gemini),
            InterviewCoachAgent(gemini),
            JobAlignmentAgent(gemini),
        ]

        context = SessionContext(session_id="test-session", user_id="test-user")
        resume = Resume(
            work=[
                Work(
                    name="Sample Company",
                    position="Sample Role",
                    highlights=["Improved performance", "Delivered features"],
                )
            ]
        )
        intent_map = {
            "ResumeCriticAgent": "RESUME_CRITIC",
            "ContentStrengthAgent": "CONTENT_STRENGTH",
            "JobAlignmentAgent": "ALIGNMENT",
            "InterviewCoachAgent": "INTERVIEW_COACH",
        }

        for agent in agents:
            agent_input = AgentInput(
                intent=intent_map[agent.get_name()],
                resume=resume,
                job_description="Sample job description for testing",
                message_history=[],
            )
            response = agent.process(agent_input, context)
            if not response.content:
                msg = f"{agent.get_name()} returned empty content"
                raise AssertionError(msg)

        return True
    finally:
        for agent_cls, original_value in original_flags.items():
            agent_cls.USE_MOCK_RESPONSE = original_value


def main() -> int:

    try:
        ok = test_agents_with_inline_mock()
    except Exception:
        return 1

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
