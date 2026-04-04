from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langfuse import Langfuse, observe, propagate_attributes

from app.agents.base import BaseAgentProtocol
from app.core.config import settings
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
from app.orchestration.persistence import get_checkpoint_store
from app.utils.json_parser import parse_json_payload
from app.utils.validators import is_valid_date, is_valid_url

langfuse = Langfuse()

INTENT_TO_AGENTS = {
    Intent.RESUME_CRITIC: ["ResumeCriticAgent"],
    Intent.CONTENT_STRENGTH: ["ContentStrengthAgent"],
    Intent.ALIGNMENT: ["JobAlignmentAgent"],
    Intent.INTERVIEW_COACH: ["InterviewCoachAgent"],
}


@dataclass
class OrchestrationState:
    request: ChatRequest
    context: SessionContext
    agent_sequence: list[str]
    artifacts: list[AnalysisArtifact] = field(default_factory=list)
    input: Optional[AgentInput] = None
    resume: Optional[Resume] = None
    resume_document: Optional[ResumeDocument] = None
    needs_review: bool = False
    review_payload: Optional[dict[str, Any]] = None
    shared_memory: dict[str, Any] = field(default_factory=dict)
    checkpoint_key: Optional[str] = None
    halt: bool = False
    review_attempts: int = 0
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
        self.checkpoints = get_checkpoint_store()
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

                state = self._resolve_state(request, context, intent)
                config = {"configurable": {"thread_id": session_id}}

                result = self.workflow.invoke(state, config=config)
                final_state = result if isinstance(result, OrchestrationState) else None
                response = (
                    final_state.response
                    if final_state is not None
                    else result.get("response")
                )

                if not response:
                    raise RuntimeError("No response produced")

                checkpoint_id = (
                    final_state.checkpoint_key
                    if final_state is not None
                    else result.get("checkpoint_id")
                )
                review_payload = (
                    final_state.review_payload
                    if final_state is not None
                    else result.get("review_payload")
                )

                self._attach_checkpoint_metadata(
                    response, checkpoint_id, review_payload
                )

                if final_state is not None:
                    context.shared_memory = final_state.shared_memory

                logger.log_orchestration_complete(
                    session_id, time.time() - start, state.agent_sequence
                )
                return response

    def _resolve_state(
        self, request: ChatRequest, context: SessionContext, intent: Intent
    ) -> OrchestrationState:
        control = getattr(request, "control", None)
        checkpoint_id = getattr(request, "checkpointId", None)
        session_id = getattr(context, "session_id", "unknown")
        sequence = INTENT_TO_AGENTS[intent]

        if control == "rewind":
            if not checkpoint_id:
                raise ValueError("checkpointId is required for rewind control")
            record = self.checkpoints.rewind(session_id, checkpoint_id)
            if record is None:
                raise ValueError("Invalid checkpointId for rewind")
            state = record.state
            state.request = request
            state.context = context
            state.agent_sequence = sequence
            state.response = None
            state.input = None
            state.halt = False
            self._apply_resume_override(state, request)
            return state

        if control == "resume":
            record = None
            if checkpoint_id:
                record = self.checkpoints.get(session_id, checkpoint_id)
            else:
                record = self.checkpoints.latest(session_id)
            if record is None:
                raise ValueError("No checkpoint available to resume")
            state = record.state
            state.request = request
            state.context = context
            state.agent_sequence = sequence
            state.review_attempts = max(state.review_attempts, 0) + 1
            state.response = None
            state.input = None
            state.halt = False
            state.needs_review = False
            state.review_payload = None
            self._apply_resume_override(state, request)
            return state

        if control:
            raise ValueError(f"Unsupported control operation: {control}")

        return OrchestrationState(
            request=request,
            context=context,
            agent_sequence=sequence,
            shared_memory=dict(context.shared_memory or {}),
        )

    def _apply_resume_override(
        self, state: OrchestrationState, request: ChatRequest
    ) -> None:
        if request.resumeData and self._has_content(request.resumeData):
            state.resume = request.resumeData
            state.resume_document = self._build_resume_doc(
                state.resume, "resumeData"
            )
            self._update_state_memory(
                state,
                current_resume=state.resume.model_dump(exclude_none=True),
            )
            return

        if request.resumeFile:
            state.resume = None
            state.resume_document = None
            state.needs_review = False
            state.review_payload = None
            self._update_state_memory(
                state,
                current_resume=None,
                extractor_confidence_score=None,
                extractor_low_confidence_fields=None,
                extractor_needs_review=None,
                extractor_validation_errors=None,
                review_payload=None,
            )

    # ---------- Workflow ----------

    def _build_workflow(self):
        graph = StateGraph(OrchestrationState)
        graph.add_node("normalize", self._normalize_resume)
        graph.add_node("hitl_review", self._hitl_review)
        graph.add_node("run_agent", self._run_agent)
        graph.set_entry_point("normalize")
        graph.add_conditional_edges(
            "normalize",
            self._route_after_normalize,
            {"review": "hitl_review", "continue": "run_agent", "end": END},
        )
        graph.add_conditional_edges(
            "run_agent",
            lambda s: "end" if s.index >= len(s.agent_sequence) else "continue",
            {"continue": "run_agent", "end": END},
        )
        graph.add_edge("hitl_review", END)
        return graph.compile(checkpointer=MemorySaver())

    def _route_after_normalize(self, state: OrchestrationState) -> str:
        if state.halt:
            return "end"
        if state.needs_review:
            return "review"
        return "continue"

    def _normalize_resume(self, state: OrchestrationState) -> OrchestrationState:
        request = state.request
        context = state.context

        resume = None
        resume_doc = None
        confidence_score = None
        low_confidence_fields: list[str] = []
        validation_errors: list[str] = []
        needs_review = False

        if state.resume and self._has_content(state.resume):
            resume = state.resume
            resume_doc = state.resume_document or self._build_resume_doc(
                resume, "resumeData"
            )
            validation_errors = self._validate_resume_data(resume)
            confidence_score = 1.0
            needs_review = bool(validation_errors)
        elif request.resumeData and self._has_content(request.resumeData):
            resume = request.resumeData
            resume_doc = self._build_resume_doc(resume, "resumeData")
            validation_errors = self._validate_resume_data(resume)
            confidence_score = 1.0
            needs_review = bool(validation_errors)
        elif request.resumeFile:
            extractor = self._get_agent("ExtractorAgent")
            try:
                response = extractor.process(
                    json.dumps(request.resumeFile.model_dump()), context
                )
                parsed = json.loads(response.content or "{}")
                resume = Resume.model_validate(parsed)
                resume_doc = self._build_resume_doc(resume, "resumeFile")
                confidence_score = response.confidence_score or 0.0
                low_confidence_fields = response.low_confidence_fields or []
                sharp_metadata = response.sharp_metadata or {}
                if isinstance(sharp_metadata, dict):
                    validation_errors = list(
                        sharp_metadata.get("validation_errors", [])
                    )
                needs_review = bool(response.needs_review) or bool(validation_errors)
            except Exception as exc:
                state.response = self._failure(
                    "Failed to parse resume file.",
                    str(exc),
                    context,
                    needs_review=True,
                )
                state.halt = True
                return state
        else:
            state.response = self._failure(
                "No resume provided.",
                "Upload resume or provide resumeData.",
                context,
            )
            state.halt = True
            return state

        if resume is None:
            state.response = self._failure(
                "Resume normalization failed.",
                "Unable to parse resume input.",
                context,
                needs_review=True,
            )
            state.halt = True
            return state

        if resume_doc is None:
            resume_doc = self._build_resume_doc(resume, "resumeData")

        review_payload = None
        if needs_review:
            review_payload = {
                "extracted_data": resume.model_dump(exclude_none=True),
                "validation_errors": validation_errors,
                "confidence_score": confidence_score,
                "fields_requiring_attention": low_confidence_fields,
            }

        state.resume = resume
        state.resume_document = resume_doc
        state.needs_review = needs_review
        state.review_payload = review_payload
        state.input = self._build_agent_input(state)

        self._update_state_memory(
            state,
            current_resume=resume.model_dump(exclude_none=True),
            extractor_confidence_score=confidence_score,
            extractor_low_confidence_fields=low_confidence_fields,
            extractor_needs_review=needs_review,
            extractor_validation_errors=validation_errors,
            review_payload=review_payload,
        )
        self._record_checkpoint(state)

        if needs_review:
            state.response = self._build_review_response(state)
        return state

    def _hitl_review(self, state: OrchestrationState) -> OrchestrationState:
        if state.response is None:
            state.response = self._build_review_response(state)
        return state

    def _run_agent(self, state: OrchestrationState) -> OrchestrationState:
        if state.index >= len(state.agent_sequence):
            return state

        if state.input is None:
            state.input = self._build_agent_input(state)

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
        self._update_state_memory(
            state, artifacts=[artifact.model_dump() for artifact in state.artifacts]
        )
        state.index += 1
        self._record_checkpoint(state)

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

    def _build_agent_input(self, state: OrchestrationState) -> AgentInput:
        request = state.request
        intent = self._parse_intent(request.intent)
        return AgentInput(
            intent=intent,
            resume=state.resume,
            resume_document=state.resume_document,
            job_description=request.jobDescription or "",
            message_history=request.messageHistory or [],
            audio_data=getattr(request, "audioData", None),
        )

    def _record_checkpoint(self, state: OrchestrationState) -> None:
        session_id = getattr(state.context, "session_id", "unknown")
        state.checkpoint_key = self.checkpoints.save(session_id, state)

    def _attach_checkpoint_metadata(
        self,
        response: AgentResponse,
        checkpoint_id: Optional[str],
        review_payload: Optional[dict[str, Any]],
    ) -> None:
        if response.sharp_metadata is None:
            response.sharp_metadata = {}
        if checkpoint_id:
            response.sharp_metadata["checkpoint_id"] = checkpoint_id
        if review_payload:
            response.sharp_metadata["review_payload"] = review_payload

    def _build_review_response(self, state: OrchestrationState) -> AgentResponse:
        payload = {
            "review_payload": state.review_payload or {},
            "metadata": {
                "review_required": True,
                "checkpoint_id": state.checkpoint_key,
            },
        }
        return AgentResponse(
            agent_name="HITL_REVIEW",
            content=json.dumps(payload),
            reasoning="HITL review required before continuing.",
            confidence_score=state.review_payload.get("confidence_score")
            if state.review_payload
            else 0.0,
            needs_review=True,
            low_confidence_fields=(
                state.review_payload.get("fields_requiring_attention", [])
                if state.review_payload
                else []
            ),
            decision_trace=state.context.decision_trace or [],
            sharp_metadata={
                "checkpoint_id": state.checkpoint_key,
                "review_payload": state.review_payload,
            },
        )

    def _update_state_memory(self, state: OrchestrationState, **kwargs) -> None:
        memory = dict(state.shared_memory or {})
        memory.update(kwargs)
        state.shared_memory = memory
        state.context.shared_memory = memory

    def _validate_resume_data(self, resume: Resume) -> list[str]:
        errors: list[str] = []
        list_fields = ["work", "education", "certificates", "projects", "awards"]
        date_fields = ["startDate", "endDate", "date"]

        for field in list_fields:
            items = getattr(resume, field, []) or []
            for item in items:
                url_value = getattr(item, "url", None)
                if url_value and not is_valid_url(url_value):
                    errors.append(f"{field}: url='{url_value}' (invalid)")
                for attr_name in date_fields:
                    attr_value = getattr(item, attr_name, None)
                    if attr_value is not None and not is_valid_date(attr_value):
                        errors.append(f"{field}: {attr_name}='{attr_value}'")
        return errors
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

                sharp_metadata = response.sharp_metadata or {}

                self._update_memory(
                    context,
                    extractor_confidence_score=response.confidence_score,
                    extractor_low_confidence_fields=response.low_confidence_fields,
                    extractor_needs_review=response.needs_review,
                    extractor_validation_errors=sharp_metadata.get(
                        "validation_errors", []
                    ),
                )

                logger.info(
                    "ExtractorAgent normalization complete",
                    session_id=getattr(context, "session_id", "unknown"),
                    confidence_score=response.confidence_score,
                    needs_review=response.needs_review,
                    low_confidence_fields=response.low_confidence_fields,
                )

                if response.needs_review:
                    return self._failure(
                    "Failed to extract meaningful information from resume file.",
                    "Failed to extract meaningful information from resume file.",
                    context,
                    needs_review=True
                )
            except Exception as e:
                return self._failure(
                    "Failed to parse resume file.",
                    str(e),
                    context,
                    needs_review=True
                )

            doc = self._build_resume_doc(resume, "resumeFile")
            self._update_memory(context, current_resume=resume.model_dump())
            return resume, doc

        return self._failure(
            "No resume provided.",
            "Upload resume or provide resumeData.",
            context,
        )

    def _failure(
        self,
        reason: str,
        details: str,
        context: SessionContext,
        needs_review: bool = False,
    ):
        metadata = {}
        if needs_review:
            metadata.update(
                {
                    "needs_review": True
                }
            )
        plan = ActionPlan(
            summary="Resume normalization failed.",
            actions=[details],
            priority="HIGH",
            no_change=False,
            metadata=metadata,
        )
        return AgentResponse(
            agent_name="NormalizeStage",
            content=json.dumps(plan.model_dump()),
            reasoning=reason,
            confidence_score=0.0,
            needs_review=needs_review,
            decision_trace=context.decision_trace or [],
        )

    # ---------- Utilities ----------

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
