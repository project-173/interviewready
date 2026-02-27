import os

from fastapi.testclient import TestClient

os.environ["DEBUG"] = "false"
os.environ.setdefault("GOOGLE_API_KEY", "test-google-api-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")

from app.core.auth import get_current_user
from app.main import app

def fake_user():
    return {"uid": "test-user-1"}

def test_agents_and_chat():
    app.dependency_overrides[get_current_user] = fake_user
    client = TestClient(app)

    r1 = client.get("/api/v1/agents")
    assert r1.status_code == 200
    assert "ResumeCriticAgent" in r1.json()

    r2 = client.post(
        "/api/v1/chat",
        params={"sessionId": "s1"},
        json={"message": "Analyze my resume"},
    )
    assert r2.status_code == 200
    assert "agent_name" in r2.json()

    app.dependency_overrides.clear()
