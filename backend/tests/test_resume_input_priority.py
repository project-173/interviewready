"""Tests for resumeData/resumeFile precedence and extraction flow."""

from __future__ import annotations

import json
from unittest.mock import patch

from app.agents.extractor import ExtractorAgent
from app.governance import SharpGovernanceService
from app.models import (
    AgentInput,
    AgentResponse,
    ChatRequest,
    Resume,
    ResumeFile,
    SessionContext,
    Work,
)
from app.orchestration import OrchestrationAgent


class StubAgent:
    def __init__(self, name: str):
        self._name = name
        self.system_prompt = f"{name} prompt"
        self.inputs: list[AgentInput | str | bytes] = []

    def get_name(self) -> str:
        return self._name

    def update_system_prompt(self, new_prompt: str) -> None:
        self.system_prompt = new_prompt

    def get_system_prompt(self) -> str:
        return self.system_prompt

    def process(
        self, input_data: AgentInput | str | bytes, context: SessionContext
    ) -> AgentResponse:
        self.inputs.append(input_data)
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
        self.needs_review = False

    def process(
        self, input_data: AgentInput | str | bytes, context: SessionContext
    ) -> AgentResponse:
        self.calls += 1
        self.inputs.append(input_data)
        return AgentResponse(
            agent_name=self._name,
            content=json.dumps({"work": [{"name": "Extracted from PDF"}]}),
            reasoning="stub extract",
            confidence_score=0.2 if self.needs_review else 1.0,
            needs_review=self.needs_review,
            low_confidence_fields=["work[0].name"] if self.needs_review else [],
            decision_trace=[],
            sharp_metadata={
                "validation_errors": ["Missing endDate for work[0]"]
                if self.needs_review
                else []
            },
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
        resumeData=Resume(work=[Work(name="Structured resume input")]),
        resumeFile=ResumeFile(data="ignored", fileType="pdf"),
    )

    orchestrator.orchestrate(request, context)

    assert extractor.calls == 0
    assert resume_agent.inputs
    input_payload = resume_agent.inputs[0]
    assert isinstance(input_payload, AgentInput)
    assert input_payload.resume
    assert input_payload.resume.work[0].name == "Structured resume input"


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
    input_payload = resume_agent.inputs[0]
    assert isinstance(input_payload, AgentInput)
    assert input_payload.resume
    assert input_payload.resume.work[0].name == "Extracted from PDF"


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
    input_payload = resume_agent.inputs[0]
    assert isinstance(input_payload, AgentInput)
    assert input_payload.resume
    assert input_payload.resume.work[0].name == "Extracted from PDF"


def test_extractor_agent_extracts_pdf_payload() -> None:
    agent = ExtractorAgent(gemini_service=object())
    context = SessionContext(session_id="s3", user_id="u3")
    payload = json.dumps({"data": "any-base64", "fileType": "pdf"})

    with patch("app.agents.extractor.parse_pdf_base64", return_value="Jane Doe Resume Text"), patch(
        "app.agents.extractor.ExtractorAgent._generate_llm_response",
        return_value=(Resume(work=[Work(name="Jane Doe Resume Text")]), 0.95, [], []),
    ):
        response = agent.process(payload, context)

    parsed = json.loads(response.content or "{}")
    assert response.agent_name == "ExtractorAgent"
    assert parsed.get("work")[0].get("name") == "Jane Doe Resume Text"


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


def test_extractor_low_confidence_triggers_hitl_review() -> None:
    governance = SharpGovernanceService()
    extractor = StubExtractorAgent()
    extractor.needs_review = True
    resume_agent = StubAgent("ResumeCriticAgent")
    orchestrator = OrchestrationAgent(
        [extractor, resume_agent],
        governance=governance,
    )
    context = SessionContext(session_id="s-review", user_id="u-review")
    request = ChatRequest(
        intent="RESUME_CRITIC",
        resumeFile=ResumeFile(data="fake-base64", fileType="pdf"),
    )

    result = orchestrator.orchestrate(request, context)

    assert result.needs_review is True
    assert result.sharp_metadata
    assert result.sharp_metadata.get("checkpoint_id")
    assert result.sharp_metadata.get("review_payload")
    assert not resume_agent.inputs


def test_resume_control_skips_extractor_after_review() -> None:
    governance = SharpGovernanceService()
    extractor = StubExtractorAgent()
    extractor.needs_review = True
    resume_agent = StubAgent("ResumeCriticAgent")
    orchestrator = OrchestrationAgent(
        [extractor, resume_agent],
        governance=governance,
    )
    context = SessionContext(session_id="s-resume", user_id="u-resume")
    request = ChatRequest(
        intent="RESUME_CRITIC",
        resumeFile=ResumeFile(data="fake-base64", fileType="pdf"),
    )

    review_response = orchestrator.orchestrate(request, context)
    checkpoint_id = (review_response.sharp_metadata or {}).get("checkpoint_id")
    assert checkpoint_id

    resume_request = ChatRequest(
        intent="RESUME_CRITIC",
        control="resume",
        checkpointId=checkpoint_id,
        resumeData=Resume(work=[Work(name="Edited Resume")]),
    )

    result = orchestrator.orchestrate(resume_request, context)

    assert extractor.calls == 1
    assert resume_agent.inputs
    input_payload = resume_agent.inputs[-1]
    assert isinstance(input_payload, AgentInput)
    assert input_payload.resume
    assert input_payload.resume.work[0].name == "Edited Resume"


def test_rewind_with_new_resume_file_reextracts() -> None:
    governance = SharpGovernanceService()
    extractor = StubExtractorAgent()
    resume_agent = StubAgent("ResumeCriticAgent")
    orchestrator = OrchestrationAgent(
        [extractor, resume_agent],
        governance=governance,
    )
    context = SessionContext(session_id="s-rewind", user_id="u-rewind")
    request = ChatRequest(
        intent="RESUME_CRITIC",
        resumeFile=ResumeFile(data="fake-base64", fileType="pdf"),
    )

    first_response = orchestrator.orchestrate(request, context)
    checkpoint_id = (first_response.sharp_metadata or {}).get("checkpoint_id")
    assert checkpoint_id

    rewind_request = ChatRequest(
        intent="RESUME_CRITIC",
        control="rewind",
        checkpointId=checkpoint_id,
        resumeFile=ResumeFile(data="new-fake-base64", fileType="pdf"),
    )

    orchestrator.orchestrate(rewind_request, context)

    assert extractor.calls == 2
