import os
import json
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ["DEBUG"] = "false"
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")

from app.core.auth import get_current_user
from app.main import app
from app.models import AgentResponse, ChatRequest

def fake_user():
    return {"uid": "test-user-1"}


class StubOrchestrator:
    """Deterministic orchestrator stub for endpoint schema tests."""

    def orchestrate(self, request: ChatRequest, context) -> AgentResponse:  # noqa: ANN001
        if request.intent == "RESUME_CRITIC":
            return AgentResponse(
                agent_name="ResumeCriticAgent",
                content=json.dumps(
                    {
                        "score": 88,
                        "readability": "Clear and concise",
                        "formattingRecommendations": [
                            "Use consistent date format",
                        ],
                        "suggestions": [
                            "Quantify outcomes in experience bullets",
                        ],
                    }
                ),
            )
        if request.intent == "CONTENT_STRENGTH":
            return AgentResponse(
                agent_name="ContentStrengthAgent",
                content=json.dumps(
                    {
                        "skills": [
                            {
                                "name": "Python",
                                "category": "Technical",
                                "confidenceScore": 0.91,
                                "evidenceStrength": "HIGH",
                                "evidence": "Built backend services with Python",
                            }
                        ],
                        "achievements": [
                            {
                                "description": "Reduced API latency",
                                "impact": "HIGH",
                                "quantifiable": True,
                                "confidenceScore": 0.89,
                                "originalText": "Reduced API latency by 30%",
                            }
                        ],
                        "suggestions": [
                            {
                                "original": "Improved performance",
                                "suggested": "Reduced API latency by 30%",
                                "rationale": "Adds measurable impact",
                                "faithful": True,
                                "confidenceScore": 0.84,
                            }
                        ],
                        "hallucinationRisk": 0.15,
                        "summary": "Strong evidence-backed profile.",
                    }
                ),
            )
        if request.intent == "ALIGNMENT":
            return AgentResponse(
                agent_name="JobAlignmentAgent",
                content=json.dumps(
                    {
                        "skillsMatch": ["Python", "FastAPI"],
                        "missingSkills": ["Kubernetes"],
                        "experienceMatch": "Strong backend alignment",
                        "fitScore": 82,
                        "reasoning": "Good core skill overlap with one cloud gap.",
                    }
                ),
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
    app.dependency_overrides[get_current_user] = fake_user
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
    assert {"score", "readability", "formattingRecommendations", "suggestions"} <= set(
        resume_payload.keys()
    )

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

    app.dependency_overrides.clear()
