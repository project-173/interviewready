"""Tests for resumeData/resumeFile precedence and extraction flow."""

from __future__ import annotations

import json
from unittest.mock import patch

from app.agents.extractor import ExtractorAgent
from app.governance import SharpGovernanceService
from app.models import AgentResponse, ChatRequest, Resume, ResumeFile, SessionContext
from app.orchestration import OrchestrationAgent


class StubAgent:
    def __init__(self, name: str):
        self._name = name
        self.system_prompt = f"{name} prompt"
        self.inputs: list[str] = []

    def get_name(self) -> str:
        return self._name

    def update_system_prompt(self, new_prompt: str) -> None:
        self.system_prompt = new_prompt

    def get_system_prompt(self) -> str:
        return self.system_prompt

    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        self.inputs.append(input_text)
        return AgentResponse(
            agent_name=self._name,
            content=json.dumps({"ok": True}),
            reasoning="stub",
            confidence_score=0.9,
            decision_trace=[],
            sharp_metadata={},
        )


class StubExtractorAgent(StubAgent):
    def __init__(self) -> None:
        super().__init__("ExtractorAgent")
        self.calls = 0

    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        self.calls += 1
        self.inputs.append(input_text)
        return AgentResponse(
            agent_name=self._name,
            content=json.dumps({"summary": "Extracted from PDF"}),
            reasoning="stub extract",
            confidence_score=1.0,
            decision_trace=[],
            sharp_metadata={},
        )


def test_orchestrator_prefers_resume_data_over_resume_file() -> None:
    governance = SharpGovernanceService()
    extractor = StubExtractorAgent()
    resume_agent = StubAgent("ResumeCriticAgent")
    orchestrator = OrchestrationAgent(
        [extractor, resume_agent],
        governance=governance,
    )
    context = SessionContext(session_id="s1", user_id="u1")
    request = ChatRequest(
        intent="RESUME_CRITIC",
        resumeData=Resume(summary="Structured resume input"),
        resumeFile=ResumeFile(data="ignored", fileType="pdf"),
    )

    orchestrator.orchestrate(request, context)

    assert extractor.calls == 0
    assert resume_agent.inputs
    assert "Structured resume input" in resume_agent.inputs[0]


def test_orchestrator_uses_extractor_when_resume_data_missing() -> None:
    governance = SharpGovernanceService()
    extractor = StubExtractorAgent()
    resume_agent = StubAgent("ResumeCriticAgent")
    orchestrator = OrchestrationAgent(
        [extractor, resume_agent],
        governance=governance,
    )
    context = SessionContext(session_id="s2", user_id="u2")
    request = ChatRequest(
        intent="RESUME_CRITIC",
        resumeFile=ResumeFile(data="fake-base64", fileType="pdf"),
    )

    orchestrator.orchestrate(request, context)

    assert extractor.calls == 1
    assert resume_agent.inputs
    assert "Extracted from PDF" in resume_agent.inputs[0]


def test_orchestrator_uses_extractor_when_resume_data_is_empty() -> None:
    governance = SharpGovernanceService()
    extractor = StubExtractorAgent()
    resume_agent = StubAgent("ResumeCriticAgent")
    orchestrator = OrchestrationAgent(
        [extractor, resume_agent],
        governance=governance,
    )
    context = SessionContext(session_id="s-empty", user_id="u-empty")
    request = ChatRequest(
        intent="RESUME_CRITIC",
        resumeData=Resume(),
        resumeFile=ResumeFile(data="fake-base64", fileType="pdf"),
    )

    orchestrator.orchestrate(request, context)

    assert extractor.calls == 1
    assert resume_agent.inputs
    assert "Extracted from PDF" in resume_agent.inputs[0]


def test_extractor_agent_extracts_pdf_payload() -> None:
    agent = ExtractorAgent(gemini_service=object())
    context = SessionContext(session_id="s3", user_id="u3")
    payload = json.dumps({"data": "any-base64", "fileType": "pdf"})

    with patch("app.agents.extractor.parse_pdf_base64", return_value="Jane Doe Resume Text"):
        response = agent.process(payload, context)

    parsed = json.loads(response.content or "{}")
    assert response.agent_name == "ExtractorAgent"
    assert parsed.get("summary") == "Jane Doe Resume Text"


def test_normalization_failure_returns_action_plan() -> None:
    governance = SharpGovernanceService()
    resume_agent = StubAgent("ResumeCriticAgent")
    orchestrator = OrchestrationAgent(
        [resume_agent],
        governance=governance,
    )
    context = SessionContext(session_id="s4", user_id="u4")
    request = ChatRequest(
        intent="RESUME_CRITIC",
        jobDescription="",
        messageHistory=[],
    )

    result = orchestrator.orchestrate(request, context)

    assert result.agent_name == "NormalizeStage"
    payload = json.loads(result.content or "{}")
    assert payload.get("summary") == "Resume normalization failed."
    assert payload.get("actions")
    assert not resume_agent.inputs
