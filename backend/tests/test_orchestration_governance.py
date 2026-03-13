"""Phase 4 tests for orchestration and governance services."""

from __future__ import annotations

from app.governance import SharpGovernanceService
from app.models.agent import AgentResponse, ChatRequest
from app.models.session import SessionContext
from app.orchestration import OrchestrationAgent


class StubAgent:
    """Simple test double for agent protocol."""

    def __init__(self, name: str, confidence: float = 0.9):
        self._name = name
        self._confidence = confidence
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
            content=f"{self._name} processed: {input_text}",
            reasoning=f"{self._name} reasoning",
            confidence_score=self._confidence,
            decision_trace=[],
            sharp_metadata={},
        )


def test_governance_flags_low_confidence() -> None:
    governance = SharpGovernanceService()
    response = AgentResponse(
        agent_name="ResumeCriticAgent",
        content="analysis",
        reasoning="reasoning",
        confidence_score=0.1,
        decision_trace=[],
        sharp_metadata={},
    )

    audited = governance.audit(response, "review my resume")

    assert audited.sharp_metadata["governance_audit"] == "flagged"
    assert "low_confidence" in audited.sharp_metadata["audit_flags"]
    assert audited.sharp_metadata["confidence_check_passed"] is False


def test_governance_content_strength_audit_flags_unfaithful() -> None:
    governance = SharpGovernanceService()
    content = """
    {
      "skills": [{"name": "Python", "evidenceStrength": "HIGH"}],
      "achievements": [{"description": "Increased throughput", "quantifiable": true}],
      "suggestions": [{"original": "did things", "suggested": "scaled platform", "faithful": false}],
      "hallucinationRisk": 0.8,
      "summary": "summary"
    }
    """
    response = AgentResponse(
        agent_name="ContentStrengthAgent",
        content=content,
        reasoning="summary",
        confidence_score=0.9,
        decision_trace=[],
        sharp_metadata={},
    )

    audited = governance.audit(response, "original input")

    assert audited.sharp_metadata["governance_audit"] == "flagged"
    assert "unfaithful_suggestions" in audited.sharp_metadata["audit_flags"]
    assert audited.sharp_metadata["high_evidence_skills_count"] == 1
    assert audited.sharp_metadata["has_quantified_achievements"] is True


def test_orchestration_chains_agents_for_first_resume_review() -> None:
    """Test that first-time resume review chains ResumeCriticAgent -> ContentStrengthAgent."""
    governance = SharpGovernanceService()
    resume_agent = StubAgent("ResumeCriticAgent")
    content_agent = StubAgent("ContentStrengthAgent")
    job_agent = StubAgent("JobAlignmentAgent")
    interview_agent = StubAgent("InterviewCoachAgent")
    orchestrator = OrchestrationAgent(
        [resume_agent, content_agent, job_agent, interview_agent],
        governance=governance,
        intent_gemini_service=None,
    )

    context = SessionContext(session_id="s1", user_id="u1")
    request = ChatRequest(
        intent="Please analyze and review my resume",
        resumeData={},
        jobDescription="",
        messageHistory=[]
    )
    result = orchestrator.orchestrate(request, context)

    # Both ResumeCriticAgent and ContentStrengthAgent should be called for first resume review
    assert result.agent_name == "ContentStrengthAgent"
    assert len(context.history or []) == 2
    assert resume_agent.inputs
    assert content_agent.inputs
    assert "Original request:" in content_agent.inputs[0]
    assert context.decision_trace[-1].startswith("Orchestrator: Routed to ContentStrengthAgent")


def test_orchestration_routes_job_alignment_keyword() -> None:
    governance = SharpGovernanceService()
    resume_agent = StubAgent("ResumeCriticAgent")
    content_agent = StubAgent("ContentStrengthAgent")
    job_agent = StubAgent("JobAlignmentAgent")
    interview_agent = StubAgent("InterviewCoachAgent")
    orchestrator = OrchestrationAgent(
        [resume_agent, content_agent, job_agent, interview_agent],
        governance=governance,
    )

    context = SessionContext(session_id="s2", user_id="u2")
    request = ChatRequest(
        intent="How does my profile match this job?",
        resumeData={},
        jobDescription="",
        messageHistory=[]
    )
    result = orchestrator.orchestrate(request, context)

    assert result.agent_name == "JobAlignmentAgent"
    assert len(context.history or []) == 1
    assert job_agent.inputs
    assert len(job_agent.inputs) == 1
