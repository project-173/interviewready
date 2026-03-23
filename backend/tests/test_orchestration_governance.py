"""Phase 4 tests for orchestration and governance services."""

from __future__ import annotations

from app.governance import SharpGovernanceService
from app.models.agent import AgentResponse, ChatRequest
from app.models import AgentInput
from app.models.session import SessionContext
from app.orchestration import OrchestrationAgent


class StubAgent:
    """Simple test double for agent protocol."""

    def __init__(self, name: str, confidence: float = 0.9):
        self._name = name
        self._confidence = confidence
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
            content=f"{self._name} processed",
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


def test_orchestration_routes_resume_critic_intent() -> None:
    """Test that ResumeCritic intent routes to ResumeCriticAgent."""
    governance = SharpGovernanceService()
    resume_agent = StubAgent("ResumeCriticAgent")
    content_agent = StubAgent("ContentStrengthAgent")
    job_agent = StubAgent("JobAlignmentAgent")
    interview_agent = StubAgent("InterviewCoachAgent")
    orchestrator = OrchestrationAgent(
        [resume_agent, content_agent, job_agent, interview_agent],
        governance=governance,
    )

    context = SessionContext(session_id="s1", user_id="u1")
    request = ChatRequest(
        intent="RESUME_CRITIC",
        resumeData={},
        jobDescription="",
        messageHistory=[]
    )
    result = orchestrator.orchestrate(request, context)

    assert result.agent_name == "ResumeCriticAgent"
    assert len(context.history or []) == 1
    assert resume_agent.inputs
    assert not content_agent.inputs
    assert context.decision_trace[-1].startswith("Orchestrator: Routed to ResumeCriticAgent")


def test_orchestration_routes_alignment_intent() -> None:
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
        intent="ALIGNMENT",
        resumeData={},
        jobDescription="",
        messageHistory=[]
    )
    result = orchestrator.orchestrate(request, context)

    assert result.agent_name == "JobAlignmentAgent"
    assert len(context.history or []) == 1
    assert job_agent.inputs
    assert len(job_agent.inputs) == 1
    artifacts = (context.shared_memory or {}).get("artifacts")
    assert isinstance(artifacts, list)
    assert artifacts and artifacts[0].get("agent") == "JobAlignmentAgent"


def test_orchestration_interview_coach_reads_from_other_agents() -> None:
    governance = SharpGovernanceService()
    resume_agent = StubAgent("ResumeCriticAgent")
    content_agent = StubAgent("ContentStrengthAgent")
    job_agent = StubAgent("JobAlignmentAgent")
    interview_agent = StubAgent("InterviewCoachAgent")
    orchestrator = OrchestrationAgent(
        [resume_agent, content_agent, job_agent, interview_agent],
        governance=governance,
    )

    context = SessionContext(session_id="s3", user_id="u3")
    request = ChatRequest(
        intent="INTERVIEW_COACH",
        resumeData={"work": ["Engineering"]},
        jobDescription="Urgent backend role",
        messageHistory=[{"role": "user", "text": "Tell me interview tips"}],
    )

    result = orchestrator.orchestrate(request, context)

    assert result.agent_name == "InterviewCoachAgent"
    assert resume_agent.inputs
    assert content_agent.inputs
    assert job_agent.inputs
    assert interview_agent.inputs

    shared_memory = context.shared_memory or {}
    assert shared_memory.get("resumecritic") == "ResumeCriticAgent processed: Resume data: {\n  \"work\": [\"Engineering\"]\n}"
    assert shared_memory.get("contentstrength") == "ContentStrengthAgent processed: Resume data: {\n  \"work\": [\"Engineering\"]\n}"
    assert shared_memory.get("jobalignment") == "JobAlignmentAgent processed: Resume data: {\n  \"work\": [\"Engineering\"]\n}\nJob Description: Urgent backend role"
