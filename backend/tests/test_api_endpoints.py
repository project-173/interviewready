import os
import json
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ["DEBUG"] = "false"
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")

from app.main import app
from app.models import AgentResponse, ChatRequest


class StubOrchestrator:
    """Deterministic orchestrator stub for endpoint schema tests."""

    def orchestrate(self, request: ChatRequest, context) -> AgentResponse:  # noqa: ANN001
        if request.intent == "RESUME_CRITIC":
            payload = {
                "score": 88,
                "readability": "Clear and concise.",
                "formattingRecommendations": ["Align dates consistently."],
                "suggestions": ["Add more quantified impact."],
            }
            return AgentResponse(
                agent_name="ResumeCriticAgent",
                content=payload,
            )
        if request.intent == "CONTENT_STRENGTH":
            payload = {
                "skills": [
                    {
                        "name": "Python",
                        "category": "Technical",
                        "confidenceScore": 0.9,
                        "evidenceStrength": "HIGH",
                        "evidence": "Built ETL pipelines.",
                    }
                ],
                "achievements": [
                    {
                        "description": "Reduced latency by 25%.",
                        "impact": "HIGH",
                        "quantifiable": True,
                        "confidenceScore": 0.8,
                        "originalText": "Improved performance.",
                    }
                ],
                "suggestions": [
                    {
                        "original": "Worked on APIs",
                        "suggested": "Designed REST APIs serving 10k rps",
                        "rationale": "Adds scale and impact",
                        "faithful": True,
                        "confidenceScore": 0.7,
                    }
                ],
                "hallucinationRisk": 0.1,
                "summary": "Strong technical evidence.",
            }
            return AgentResponse(
                agent_name="ContentStrengthAgent",
                content=payload,
            )
        if request.intent == "ALIGNMENT":
            payload = {
                "skillsMatch": ["Python", "SQL"],
                "missingSkills": ["Kubernetes"],
                "experienceMatch": "Strong backend alignment.",
                "fitScore": 82,
                "reasoning": "Most core skills are present.",
                "sources": [],
            }
            return AgentResponse(
                agent_name="JobAlignmentAgent",
                content=payload,
            )

        return AgentResponse(
            agent_name="InterviewCoachAgent",
            content="Tell me about a challenging project you delivered end-to-end.",
        )


def _chat_request_payload(intent: str) -> dict:
    return {
        "intent": intent,
        "resumeData": {},
        "jobDescription": "Some JD text",
        "messageHistory": [],
    }


def test_agents_and_chat():
    client = TestClient(app)

    r1 = client.get("/api/v1/agents")
    assert r1.status_code == 200
    assert "ResumeCriticAgent" in r1.json()

    with patch(
        "app.api.v1.endpoints.chat.get_orchestration_agent",
        return_value=StubOrchestrator(),
    ):
        resume_response = client.post(
            "/api/v1/chat",
            params={"sessionId": "s1"},
            json=_chat_request_payload("RESUME_CRITIC"),
        )
        content_response = client.post(
            "/api/v1/chat",
            params={"sessionId": "s1"},
            json=_chat_request_payload("CONTENT_STRENGTH"),
        )
        alignment_response = client.post(
            "/api/v1/chat",
            params={"sessionId": "s1"},
            json=_chat_request_payload("ALIGNMENT"),
        )
        interview_response = client.post(
            "/api/v1/chat",
            params={"sessionId": "s1"},
            json=_chat_request_payload("INTERVIEW_COACH"),
        )

    assert resume_response.status_code == 200
    resume_payload = resume_response.json()["payload"]
    assert {
        "score",
        "readability",
        "formattingRecommendations",
        "suggestions",
    } <= set(resume_payload.keys())

    assert content_response.status_code == 200
    content_payload = content_response.json()["payload"]
    assert {
        "skills",
        "achievements",
        "suggestions",
        "hallucinationRisk",
        "summary",
    } <= set(content_payload.keys())

    assert alignment_response.status_code == 200
    alignment_payload = alignment_response.json()["payload"]
    assert {
        "skillsMatch",
        "missingSkills",
        "experienceMatch",
        "fitScore",
        "reasoning",
    } <= set(alignment_payload.keys())

    assert interview_response.status_code == 200
    assert isinstance(interview_response.json()["payload"], str)


def test_chat_rejects_invalid_intent():
    client = TestClient(app)

    response = client.post(
        "/api/v1/chat",
        params={"sessionId": "s-invalid"},
        json=_chat_request_payload("UNKNOWN_INTENT"),
    )

    assert response.status_code == 422
