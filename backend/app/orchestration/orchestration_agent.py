from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Optional

from langgraph.graph import END, StateGraph
from langfuse import Langfuse, observe, propagate_attributes

from app.agents.base import BaseAgentProtocol
from app.core.logging import logger
from app.governance.sharp_governance_service import SharpGovernanceService
from app.models.agent import (
    ActionPlan,
    AnalysisArtifact,
    AgentResponse,
    ChatRequest,
    ResumeDocument,
)
from app.models.agent import AgentInput, Intent
from app.models.resume import Resume
from app.models.session import SessionContext
from app.utils.json_parser import parse_json_payload

langfuse = Langfuse()

INTENT_TO_AGENTS = {
    Intent.RESUME_CRITIC: ["ResumeCriticAgent"],
    Intent.CONTENT_STRENGTH: ["ContentStrengthAgent"],
    Intent.ALIGNMENT: ["JobAlignmentAgent"],
    Intent.INTERVIEW_COACH: ["InterviewCoachAgent"],
}


@dataclass
class OrchestrationState:
    input: AgentInput
    context: SessionContext
    agent_sequence: list[str]
    artifacts: list[AnalysisArtifact]
    index: int = 0
    response: Optional[AgentResponse] = None


# ---------- Orchestrator ----------

class OrchestrationAgent:
    def __init__(
        self,
        agent_list: list[BaseAgentProtocol],
        governance: SharpGovernanceService,
    ):
        self.agent_list = {a.get_name(): a for a in agent_list}
        self.governance = governance
        self.workflow = self._build_workflow()

    def get_agents(self) -> dict[str, BaseAgentProtocol]:
        """Return the registered agents keyed by name."""
        return self.agent_list

    # ---------- Public API ----------

    @observe(name="orchestration_execution")
    def orchestrate(self, request: ChatRequest, context: SessionContext) -> AgentResponse:
        start = time.time()
        session_id = getattr(context, "session_id", "unknown")
        user_id = getattr(context, "user_id", None)

        with langfuse.start_as_current_observation(name="orchestration_execution"):
            with propagate_attributes(user_id=user_id, session_id=session_id):

                intent = self._parse_intent(request.intent)
                if request.jobDescription:
                    context.job_description = request.jobDescription
                normalized = self._normalize_or_fail(request, context)
                if isinstance(normalized, AgentResponse):
                    return normalized

                resume, resume_doc = normalized

                agent_input = AgentInput(
                    intent=intent,
                    resume=resume,
                    resume_document=resume_doc,
                    job_description=request.jobDescription or "",
                    message_history=request.messageHistory or [],
                    audio_data=getattr(request, "audioData", None),
                )

                sequence = INTENT_TO_AGENTS[intent]

                state = OrchestrationState(
                    input=agent_input,
                    context=context,
                    agent_sequence=sequence,
                    artifacts=[],
                )

                result = self.workflow.invoke(state)
                response = result.get("response")

                if not response:
                    raise RuntimeError("No response produced")

                logger.log_orchestration_complete(
                    session_id, time.time() - start, sequence
                )
                return response

    # ---------- Workflow ----------

    def _build_workflow(self):
        graph = StateGraph(OrchestrationState)
        graph.add_node("run_agent", self._run_agent)
        graph.set_entry_point("run_agent")
        graph.add_conditional_edges(
            "run_agent",
            lambda s: "end" if s.index >= len(s.agent_sequence) else "continue",
            {"continue": "run_agent", "end": END},
        )
        return graph.compile()

    def _run_agent(self, state: OrchestrationState) -> OrchestrationState:
        if state.index >= len(state.agent_sequence):
            return state

        agent_name = state.agent_sequence[state.index]
        agent = self._get_agent(agent_name)

        context = state.context
        session_id = getattr(context, "session_id", "unknown")

        input_text = self._render_input(state.input)

        logger.log_agent_execution_start(
            agent_name, input_text, session_id, state.index
        )

        start = time.time()
        response = agent.process(state.input, context)

        logger.log_agent_execution_complete(
            agent_name, response, session_id, time.time() - start
        )

        audited = self.governance.audit(response, input_text)
        self._update_context(context, audited, agent_name)

        state.response = audited
        state.artifacts.append(self._build_artifact(audited, agent_name))
        self._update_memory(context, artifacts=[artifact.model_dump() for artifact in state.artifacts])
        state.index += 1

        return state

    # ---------- Core Helpers ----------

    def _parse_intent(self, raw: str) -> Intent:
        try:
            return Intent(raw)
        except ValueError:
            raise ValueError(f"Unsupported intent: {raw}")

    def _get_agent(self, name: str) -> BaseAgentProtocol:
        if name not in self.agent_list:
            raise RuntimeError(f"Missing agent: {name}")
        return self.agent_list[name]

    def _normalize_or_fail(
        self, request: ChatRequest, context: SessionContext
    ) -> tuple[Resume, ResumeDocument] | AgentResponse:

        if request.resumeData and self._has_content(request.resumeData):
            resume = request.resumeData
            doc = self._build_resume_doc(resume, "resumeData")
            self._update_memory(context, current_resume=resume.model_dump())
            return resume, doc

        if request.resumeFile:
            extractor = self._get_agent("ExtractorAgent")
            try:
                response = extractor.process(
                    json.dumps(request.resumeFile.model_dump()), context
                )
                parsed = json.loads(response.content or "{}")
                resume = Resume.model_validate(parsed)
            except Exception as e:
                return self._failure("Failed to parse resume file.", str(e), context)

            doc = self._build_resume_doc(resume, "resumeFile")
            self._update_memory(context, current_resume=resume.model_dump())
            return resume, doc

        return self._failure(
            "No resume provided.",
            "Upload resume or provide resumeData.",
            context,
        )

    def _failure(self, reason: str, details: str, context: SessionContext):
        plan = ActionPlan(
            summary="Resume normalization failed.",
            actions=[details],
            priority="HIGH",
            no_change=False,
        )
        return AgentResponse(
            agent_name="NormalizeStage",
            content=json.dumps(plan.model_dump()),
            reasoning=reason,
            confidence_score=0.0,
            decision_trace=context.decision_trace or [],
        )

    # ---------- Utilities ----------

    def _update_memory(self, context: SessionContext, **kwargs):
        memory = dict(context.shared_memory or {})
        memory.update(kwargs)
        context.shared_memory = memory

    def _update_context(self, context: SessionContext, response, agent_name: str):
        trace = list(context.decision_trace or [])
        trace.append(f"Routed to {agent_name}")
        context.decision_trace = trace
        context.add_to_history(response)

    def _render_input(self, agent_input: AgentInput) -> str:
        data = (
            agent_input.resume.model_dump(exclude_none=True)
            if agent_input.resume is not None
            else {}
        )
        # Handle cases where agent_input.intent might be an Enum or a string
        intent_value = (
            agent_input.intent.value
            if hasattr(agent_input.intent, "value")
            else agent_input.intent
        )
        if intent_value == Intent.ALIGNMENT.value:
            return f"{json.dumps(data, indent=2)}\nJD: {agent_input.job_description}"
        return json.dumps(data, indent=2)

    def _build_resume_doc(self, resume: Resume, source: str) -> ResumeDocument:
        raw = json.dumps(resume.model_dump(exclude_none=True), indent=2)
        return ResumeDocument(source=source, raw_text=raw)

    def _has_content(self, resume: Resume) -> bool:
        def _contains_value(value: Any) -> bool:
            if value is None:
                return False
            if isinstance(value, str):
                return bool(value.strip())
            if isinstance(value, dict):
                return any(_contains_value(item) for item in value.values())
            if isinstance(value, list):
                return any(_contains_value(item) for item in value)
            return True

        return _contains_value(resume.model_dump(exclude_none=True))

    def _build_artifact(self, response: AgentResponse, agent_name: str):
        parsed = parse_json_payload(response.content or "", allow_array=True)
        return AnalysisArtifact(
            agent=agent_name,
            artifact_type=agent_name,
            payload=parsed or response.content,
            confidence_score=response.confidence_score,
        )
