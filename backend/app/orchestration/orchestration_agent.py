"""LangGraph-based orchestration service for routing across agents."""

from __future__ import annotations

import json
import time
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.base import BaseAgentProtocol
from app.agents.gemini_service import GeminiService
from app.core.langfuse_client import langfuse
from app.core.logging import logger
from app.governance.sharp_governance_service import SharpGovernanceService
from app.models.agent import (
    ActionPlan,
    AnalysisArtifact,
    AgentResponse,
    ChatRequest,
    NormalizationFailure,
    ResumeDocument,
)
from app.models.resume import Resume
from app.models.session import SessionContext
from app.utils.json_parser import parse_json_object, parse_json_payload

class OrchestrationState(TypedDict):
    """Workflow state used by LangGraph orchestration."""

    original_input: str
    current_input: str
    context: SessionContext
    agent_sequence: list[str]
    current_index: int
    current_response: AgentResponse | None
    artifacts: list[AnalysisArtifact]

class OrchestrationAgent:
    """Routes user input to one or more specialist agents."""

    def __init__(
        self,
        agent_list: list[BaseAgentProtocol],
        governance: SharpGovernanceService,
    ) -> None:
        self.agents = {agent.get_name(): agent for agent in agent_list}
        self.governance = governance
        self.workflow = self._build_workflow()

    def orchestrate(self, request: ChatRequest, context: SessionContext) -> AgentResponse:
        """Run intent analysis and execute selected agent sequence."""
        start_time = time.time()
        session_id = getattr(context, "session_id", "unknown")
        user_id = getattr(context, "user_id", None)

        with langfuse.trace(
            name="orchestration_execution",
            session_id=session_id,
            metadata={
                "user_id": user_id,
                "intent": request.intent,
            },
        ) as trace:
            # Extract intent from request and build input text for agents
            intent = request.intent
            if intent not in {"RESUME_CRITIC", "CONTENT_STRENGTH", "ALIGNMENT", "INTERVIEW_COACH"}:
                raise ValueError(f"Unsupported intent: {intent}")
            logger.log_state_transition("orchestration_start", "normalize_resume", session_id, intent=intent)
            normalization_result = self._normalize_resume(request, context)
            if isinstance(normalization_result, NormalizationFailure):
                logger.log_state_transition(
                    "normalize_resume",
                    "normalize_failed",
                    session_id,
                    reason=normalization_result.reason,
                )
                return self._build_normalization_failure_response(normalization_result, context)
            resume_model, _resume_document = normalization_result
            resume_data = (
                resume_model.model_dump(exclude_none=True)
                if resume_model is not None
                else {}
            )
            job_description = request.jobDescription or ""
            message_history = request.messageHistory or []

            # Build input text based on intent and available data
            input_text = self._build_agent_input(
                intent, resume_data, job_description, message_history
            )

                    # For intent analysis, use the original request text, not the processed intent
            original_input = request.intent or ""

            # Log orchestration start
            logger.log_orchestration_start(input_text, session_id, user_id)

            try:
                # DYNAMIC INTENT ANALYSIS: Use LLM if available and requested intent is general/missing
                if self.intent_gemini_service and (not intent or intent == "GENERAL"):
                    logger.debug("Using dynamic LLM intent analysis", session_id=session_id)
                    agent_sequence = self._analyze_intent_with_llm(input_text, context)
                else:
                    # Map intent to agent sequence directly
                    agent_sequence = self._analyze_intent(original_input, context)

                trace.update(output={"agent_sequence": agent_sequence})
                logger.log_intent_analysis(input_text, agent_sequence, "hybrid_routing", session_id)
                
                state: OrchestrationState = {
                    "original_input": input_text,
                    "current_input": input_text,
                    "context": context,
                    "agent_sequence": agent_sequence,
                    "current_index": 0,
                    "current_response": None,
                }
                
                logger.log_state_transition("orchestration_start", "workflow_execution", session_id, agent_sequence=agent_sequence)
                result = self.workflow.invoke(state)
                current_response = result.get("current_response")
                
                if current_response is None:
                    raise RuntimeError("Orchestration completed without an agent response.")
                
                total_time = time.time() - start_time
                logger.log_orchestration_complete(session_id, total_time, agent_sequence)
                
                trace.update(output={"success": True, "duration_s": total_time})
                return current_response
                
            except Exception as e:
                trace.update(output={"error": str(e)})
                logger.log_agent_error("OrchestrationAgent", e, session_id)
                raise

    def get_agents(self) -> dict[str, BaseAgentProtocol]:
        """Expose registered agent map."""
        return self.agents

    def _build_workflow(self):  # type: ignore[no-untyped-def]
        workflow = StateGraph(OrchestrationState)
        workflow.add_node("execute_agent", self._execute_agent_node)
        workflow.set_entry_point("execute_agent")
        workflow.add_conditional_edges(
            "execute_agent",
            self._route_next_step,
            {"continue": "execute_agent", "end": END},
        )
        return workflow.compile()

    def _execute_agent_node(self, state: OrchestrationState) -> dict[str, Any]:
        agent_sequence = state["agent_sequence"]
        current_index = state["current_index"]
        context = state["context"]
        session_id = getattr(context, 'session_id', 'unknown')

        if current_index >= len(agent_sequence):
            logger.debug("Agent execution complete - reached end of sequence", session_id=session_id, current_index=current_index, sequence_length=len(agent_sequence))
            return state

        agent_name = agent_sequence[current_index]
        agent = self.agents.get(agent_name)
        if agent is None:
            available = ", ".join(sorted(self.agents.keys()))
            error = RuntimeError(f"No agent found for target: {agent_name}. Available agents: {available}")
            logger.log_agent_error(agent_name, error, session_id)
            raise error

        current_input = state["current_input"]
        
        # Log agent execution start
        logger.log_agent_execution_start(agent_name, current_input, session_id, current_index)

        with langfuse.trace(
            name="orchestrator_agent_execution",
            session_id=session_id,
            metadata={
                "agent": agent_name,
                "agent_index": current_index,
                "current_input_length": len(current_input),
            },
        ) as span:
            agent_start_time = time.time()
            try:
                response = agent.process(current_input, context)
                agent_execution_time = time.time() - agent_start_time

                span.update(
                    output={
                        "response_length": len(str(response.content or "")),
                        "duration_ms": round(agent_execution_time * 1000, 2),
                    }
                )

                # Log successful agent execution
                logger.log_agent_execution_complete(agent_name, response, session_id, agent_execution_time)

            except Exception as e:
                agent_execution_time = time.time() - agent_start_time
                span.update(output={"error": str(e), "duration_ms": round(agent_execution_time * 1000, 2)})
                logger.log_agent_error(agent_name, e, session_id)
                raise

        trace = list(context.decision_trace or [])
        trace.append(f"Orchestrator: Routed to {agent_name} based on intent analysis.")
        response.decision_trace = trace

        audited_response = self.governance.audit(response, current_input)

        # ADD SHAP METADATA TO LANGFUSE (Mocked if langfuse not enabled)
        if hasattr(audited_response, 'scores') and audited_response.scores:
            logger.debug("Attaching SHAP scores to decision trace", session_id=session_id)
            trace.append(f"SHAP Analysis: {json.dumps(audited_response.scores)}")

        context.add_to_history(audited_response)
        context.decision_trace = trace
        
        logger.debug("Governance audit completed", session_id=session_id, agent_name=agent_name, governance_passed=True)

        artifacts = list(state.get("artifacts", []))
        artifacts.append(self._build_artifact(audited_response, agent_name))
        self._store_artifacts_in_context(artifacts, context)

        next_input = current_input
        return {
            "original_input": state["original_input"],
            "current_input": next_input,
            "context": context,
            "agent_sequence": agent_sequence,
            "current_index": current_index + 1,
            "current_response": audited_response,
            "artifacts": artifacts,
        }

    @staticmethod
    def _route_next_step(state: OrchestrationState) -> str:
        if state["current_index"] >= len(state["agent_sequence"]):
            return "end"
        return "continue"

    def _build_agent_input(self, intent: str, resume_data: dict, job_description: str, message_history: list) -> str:
        """Build input text for agents based on intent and available data."""
        if intent == "RESUME_CRITIC":
            return f"Resume data: {json.dumps(resume_data, indent=2)}"
        
        elif intent == "CONTENT_STRENGTH":
            return f"Resume data: {json.dumps(resume_data, indent=2)}"
        
        elif intent == "ALIGNMENT":
            return f"Resume data: {json.dumps(resume_data, indent=2)}\nJob Description: {job_description}"
        
        elif intent == "INTERVIEW_COACH":
            history_str = json.dumps([{"role": msg.role, "text": msg.text} for msg in message_history], indent=2)
            return f"Alignment data: {job_description}\nConversation history: {history_str}"
        
        else:
            # Fallback
            return f"Request data: {json.dumps(resume_data, indent=2)}"

    def _normalize_resume(
        self, request: ChatRequest, context: SessionContext
    ) -> tuple[Resume, ResumeDocument] | NormalizationFailure:
        """Normalize resume inputs into a Resume + ResumeDocument pair."""
        session_id = getattr(context, "session_id", "unknown")

        if request.resumeData is not None:
            if self._has_resume_content(request.resumeData):
                logger.debug(
                    "Orchestrator using resumeData payload",
                    session_id=session_id,
                    source="resumeData",
                )
                self._store_resume_in_context(request.resumeData, context)
                resume_document = self._build_resume_document_from_resume(
                    request.resumeData,
                    source="resumeData",
                )
                self._store_resume_document_in_context(resume_document, context)
                return request.resumeData, resume_document
            logger.debug(
                "resumeData payload is empty, checking resumeFile fallback",
                session_id=session_id,
                source="resumeData",
            )

        if request.resumeFile is not None:
            logger.debug(
                "Orchestrator invoking ExtractorAgent for resumeFile",
                session_id=session_id,
                source="resumeFile",
            )
            try:
                resume = self._extract_resume_from_file(
                    request.resumeFile.model_dump(), context
                )
            except Exception as exc:
                return NormalizationFailure(
                    reason="Failed to normalize resume file.",
                    recovery_steps="Upload a valid PDF resume and ensure it is not password protected.",
                    details=str(exc),
                )
            self._store_resume_in_context(resume, context)
            resume_document = self._resume_document_from_context(context)
            if resume_document is None:
                resume_document = self._build_resume_document_from_resume(
                    resume, source="resumeFile"
                )
                self._store_resume_document_in_context(resume_document, context)
            return resume, resume_document

        memory_resume = self._resume_from_context(context)
        if memory_resume is not None:
            logger.debug(
                "Orchestrator using resume from shared session memory",
                session_id=session_id,
                source="shared_memory",
            )
            resume_document = self._resume_document_from_context(context)
            if resume_document is None:
                resume_document = self._build_resume_document_from_resume(
                    memory_resume, source="shared_memory"
                )
                self._store_resume_document_in_context(resume_document, context)
            return memory_resume, resume_document

        logger.debug("No resume input provided in request", session_id=session_id)
        return NormalizationFailure(
            reason="No resume provided for normalization.",
            recovery_steps="Upload a PDF resume or provide resumeData in the request payload.",
        )

    def _extract_resume_from_file(
        self, resume_file_payload: dict[str, Any], context: SessionContext
    ) -> Resume:
        extractor = self.agents.get("ExtractorAgent")
        if extractor is None:
            raise RuntimeError("ExtractorAgent is required when resumeFile is provided.")

        response = extractor.process(json.dumps(resume_file_payload), context)
        if response.sharp_metadata:
            resume_document = response.sharp_metadata.get("resume_document")
            if isinstance(resume_document, dict):
                shared_memory = dict(context.shared_memory or {})
                shared_memory["resume_document"] = resume_document
                context.shared_memory = shared_memory
        parsed = parse_json_object(response.content or "")
        if not parsed:
            raise ValueError("ExtractorAgent returned invalid JSON for resumeFile payload.")

        resume = Resume.model_validate(parsed)
        trace = list(context.decision_trace or [])
        trace.append(
            "Orchestrator: Used ExtractorAgent for resumeFile after missing resumeData."
        )
        context.decision_trace = trace
        return resume

    def _build_normalization_failure_response(
        self, failure: NormalizationFailure, context: SessionContext
    ) -> AgentResponse:
        actions = [failure.recovery_steps] if failure.recovery_steps else []
        action_plan = ActionPlan(
            summary="Resume normalization failed.",
            actions=actions,
            priority="HIGH",
            no_change=False,
            metadata={
                "stage": "normalize_resume",
                "failure_reason": failure.reason,
                "details": failure.details,
            },
        )
        trace = list(context.decision_trace or [])
        trace.append("Orchestrator: Normalization failed, returning recovery ActionPlan.")
        context.decision_trace = trace
        return AgentResponse(
            agent_name="NormalizeStage",
            content=json.dumps(action_plan.model_dump(exclude_none=True), indent=2),
            reasoning=failure.reason,
            confidence_score=0.0,
            decision_trace=trace,
            sharp_metadata={"normalization_failed": True},
        )

    @staticmethod
    def _build_artifact(
        response: AgentResponse, agent_name: str
    ) -> AnalysisArtifact:
        parsed = parse_json_payload(response.content or "", allow_array=True)
        payload: dict[str, Any] | list[Any] | str
        if parsed is None:
            payload = response.content or ""
        else:
            payload = parsed
        metadata = {}
        if response.sharp_metadata:
            metadata["governance"] = response.sharp_metadata
        return AnalysisArtifact(
            agent=agent_name,
            artifact_type=agent_name,
            payload=payload,
            confidence_score=response.confidence_score,
            metadata=metadata,
        )

    @staticmethod
    def _store_artifacts_in_context(
        artifacts: list[AnalysisArtifact], context: SessionContext
    ) -> None:
        shared_memory = dict(context.shared_memory or {})
        shared_memory["artifacts"] = [
            artifact.model_dump(exclude_none=True) for artifact in artifacts
        ]
        context.shared_memory = shared_memory

    @staticmethod
    def _build_resume_document_from_resume(resume: Resume, source: str) -> ResumeDocument:
        data = resume.model_dump(exclude_none=True)
        raw_text = (
            json.dumps(data, indent=2)
            if OrchestrationAgent._has_resume_content(resume)
            else ""
        )
        warnings: list[str] = []
        if not raw_text:
            warnings.append("resume content is empty; raw_text unavailable")
        return ResumeDocument(
            source=source,
            raw_text=raw_text or None,
            warnings=warnings,
        )

    @staticmethod
    def _store_resume_document_in_context(
        resume_document: ResumeDocument, context: SessionContext
    ) -> None:
        shared_memory = dict(context.shared_memory or {})
        shared_memory["resume_document"] = resume_document.model_dump(exclude_none=True)
        context.shared_memory = shared_memory

    @staticmethod
    def _resume_document_from_context(
        context: SessionContext,
    ) -> ResumeDocument | None:
        memory = context.shared_memory or {}
        raw_document = memory.get("resume_document")
        if not isinstance(raw_document, dict) or not raw_document:
            return None
        try:
            return ResumeDocument.model_validate(raw_document)
        except Exception:
            return None

    @staticmethod
    def _has_resume_content(resume: Resume) -> bool:
        """Check whether resumeData has meaningful content beyond defaults."""
        data = resume.model_dump(exclude_none=True)
        if not data:
            return False
        for value in data.values():
            if isinstance(value, list) and value:
                return True
            if isinstance(value, str) and value.strip():
                return True
            if isinstance(value, bool) and value:
                return True
            if isinstance(value, dict) and value:
                return True
        return False

    @staticmethod
    def _store_resume_in_context(resume: Resume, context: SessionContext) -> None:
        shared_memory = dict(context.shared_memory or {})
        shared_memory["current_resume"] = resume.model_dump(exclude_none=True)
        context.shared_memory = shared_memory

    @staticmethod
    def _resume_from_context(context: SessionContext) -> Resume | None:
        memory = context.shared_memory or {}
        raw_resume = memory.get("current_resume")
        if not isinstance(raw_resume, dict) or not raw_resume:
            return None
        try:
            resume = Resume.model_validate(raw_resume)
        except Exception:
            return None
        return resume if OrchestrationAgent._has_resume_content(resume) else None

    def _map_intent_to_agents(self, intent: str) -> list[str]:
        """Map intent directly to agent sequence."""
        intent_mapping = {
            "RESUME_CRITIC": ["ResumeCriticAgent"],
            "CONTENT_STRENGTH": ["ContentStrengthAgent"],
            "ALIGNMENT": ["JobAlignmentAgent"],
            "INTERVIEW_COACH": ["InterviewCoachAgent"]
        }
        
        if intent not in intent_mapping:
            raise ValueError(f"Unsupported intent: {intent}")
        return intent_mapping[intent]
