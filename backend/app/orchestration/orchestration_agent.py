from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Optional

from langgraph.graph import END, StateGraph

from app.agents.base import BaseAgentProtocol
from app.core.langfuse_client import langfuse, propagate_attributes, get_propagated_attrs
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


class OrchestrationAgent:
    def __init__(
        self,
        agent_list: list[BaseAgentProtocol],
        governance: SharpGovernanceService,
    ):
        self.agent_list = {a.get_name(): a for a in agent_list}
        self.governance = governance
        self.workflow = self._build_workflow()

    # ---------- Public API ----------

    def orchestrate(self, request: ChatRequest, context: SessionContext) -> AgentResponse:
        start = time.time()
        session_id = getattr(context, "session_id", "unknown")
        user_id = getattr(context, "user_id", None)

        # Top-level trace — groups everything under one orchestration run
        with langfuse.trace(
            name="orchestration_execution",
            session_id=session_id,
            metadata={
                "user_id": user_id,
                "intent": request.intent,
                "has_resume_data": bool(request.resumeData),
                "has_resume_file": bool(request.resumeFile),
                "has_job_description": bool(request.jobDescription),
            },
        ) as trace:

            # Propagate session/user context so nested spans inherit it automatically
            with propagate_attributes(session_id=session_id, user_id=user_id):
                try:
                    intent = self._parse_intent(request.intent)

                    # Span: intent parsing decision
                    with trace.span(name="intent_resolution") as span:
                        span.update(output={
                            "resolved_intent": intent.value,
                            "mapped_agents": INTENT_TO_AGENTS.get(intent, []),
                        })

                    # Span: resume normalization
                    with trace.span(name="resume_normalization") as span:
                        normalized = self._normalize_or_fail(request, context)
                        if isinstance(normalized, AgentResponse):
                            span.update(output={
                                "status": "failed",
                                "reason": normalized.reasoning,
                            })
                            trace.update(output={"status": "failed", "reason": normalized.reasoning})
                            return normalized
                        resume, resume_doc = normalized
                        span.update(output={
                            "status": "success",
                            "source": resume_doc.source,
                        })

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

                    # Span: full workflow execution
                    with trace.span(name="workflow_execution") as span:
                        result = self.workflow.invoke(state)
                        response = result.get("response")

                        if not response:
                            raise RuntimeError("No response produced")

                        span.update(output={
                            "agents_executed": sequence,
                            "artifact_count": len(result.get("artifacts", [])),
                            "confidence_score": response.confidence_score,
                        })

                    elapsed = time.time() - start
                    trace.update(output={
                        "status": "success",
                        "duration_seconds": round(elapsed, 3),
                        "agents_executed": sequence,
                        "final_agent": response.agent_name,
                        "confidence_score": response.confidence_score,
                    })

                    logger.log_orchestration_complete(session_id, elapsed, sequence)
                    return response

                except Exception as e:
                    trace.update(output={
                        "status": "error",
                        "error": str(e),
                        "duration_seconds": round(time.time() - start, 3),
                    })
                    raise

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

        logger.log_agent_execution_start(agent_name, input_text, session_id, state.index)
        start = time.time()

        # Per-agent span — gives individual traceability for each agent decision
        with langfuse.trace(
            name=f"{agent_name}_execution",
            session_id=session_id,
            metadata={
                **get_propagated_attrs(),           # inherits user_id etc. from propagate_attributes
                "agent_name": agent_name,
                "agent_index": state.index,
                "intent": str(state.input.intent) if state.input.intent else None,
                "input_length": len(input_text),
            },
        ) as trace:
            try:
                response = agent.process(state.input, context)
                elapsed = time.time() - start

                audited = self.governance.audit(response, input_text)

                # Log the agent's decision and governance outcome
                trace.update(output={
                    "status": "success",
                    "duration_seconds": round(elapsed, 3),
                    "confidence_score": audited.confidence_score,
                    "response_length": len(str(audited.content or "")),
                    "decision_trace": audited.decision_trace,
                    "governance_applied": audited != response,  # True if governance modified it
                })

                logger.log_agent_execution_complete(agent_name, response, session_id, elapsed)

            except Exception as e:
                trace.update(output={
                    "status": "error",
                    "error": str(e),
                    "agent_name": agent_name,
                    "duration_seconds": round(time.time() - start, 3),
                })
                raise

        self._update_context(context, audited, agent_name)
        state.response = audited
        state.artifacts.append(self._build_artifact(audited, agent_name))
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
            if agent_input.resume
            else {}
        )
        if agent_input.intent == Intent.ALIGNMENT.value:
            return f"{json.dumps(data, indent=2)}\nJD: {agent_input.job_description}"
        return json.dumps(data, indent=2)

    def _build_resume_doc(self, resume: Resume, source: str) -> ResumeDocument:
        raw = json.dumps(resume.model_dump(exclude_none=True), indent=2)
        return ResumeDocument(source=source, raw_text=raw)

    def _has_content(self, resume: Resume) -> bool:
        return bool(resume.model_dump(exclude_none=True))

    def _build_artifact(self, response: AgentResponse, agent_name: str):
        parsed = parse_json_payload(response.content or "", allow_array=True)
        return AnalysisArtifact(
            agent=agent_name,
            artifact_type=agent_name,
            payload=parsed or response.content,
            confidence_score=response.confidence_score,
        )