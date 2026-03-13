"""LangGraph-based orchestration service for routing across agents."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Union
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents.base import BaseAgentProtocol
from app.agents.gemini_service import GeminiService
from app.core.logging import logger
from app.governance.sharp_governance_service import SharpGovernanceService
from app.models.agent import AgentResponse, ChatRequest
from app.models.resume import Resume
from app.models.session import SessionContext
from app.utils.json_parser import parse_json_object

class OrchestrationState(TypedDict):
    """Workflow state used by LangGraph orchestration."""

    original_input: Union[str, bytes]
    current_input: Union[str, bytes]
    context: SessionContext
    agent_sequence: list[str]
    current_index: int
    current_response: AgentResponse | None

class OrchestrationAgent:
    """Routes user input to one or more specialist agents."""

    INTENT_ANALYSIS_PROMPT = """
You are an intent classifier for a multi-agent resume analysis system. Analyze the user's input and determine which agent(s) should handle it.

Available agents:
- ResumeCriticAgent: General resume analysis, structure, ATS compatibility, overall feedback
- JobAlignmentAgent: Matching resume to specific job descriptions, gap analysis
- InterviewCoachAgent: Interview preparation, mock interviews, behavioral questions
- ContentStrengthAgent: Skill extraction, evidence evaluation, phrasing improvements, strength analysis

Respond with ONLY a JSON array of agent names in execution order, e.g.: ["ResumeCriticAgent", "ContentStrengthAgent"]

Rules:
- For general resume questions, use ResumeCriticAgent
- For skill/strength/achievement analysis, use ContentStrengthAgent
- For job matching questions, use JobAlignmentAgent
- For interview preparation, use InterviewCoachAgent
- Multiple agents can be chained: ResumeCriticAgent can be followed by ContentStrengthAgent for detailed analysis
- Consider conversation context when determining intent

User input: %s

Previous context: %s

Respond with ONLY the JSON array, no other text.
"""

    def __init__(
        self,
        agent_list: list[BaseAgentProtocol],
        governance: SharpGovernanceService,
        intent_gemini_service: GeminiService | None = None,
    ) -> None:
        self.agents = {agent.get_name(): agent for agent in agent_list}
        self.governance = governance
        self.intent_gemini_service = intent_gemini_service
        self.workflow = self._build_workflow()

    def orchestrate(self, request: ChatRequest, context: SessionContext) -> AgentResponse:
        """Run intent analysis and execute selected agent sequence."""
        start_time = time.time()
        session_id = getattr(context, 'session_id', 'unknown')
        user_id = getattr(context, 'user_id', None)
        
        # Extract intent from request and build input text for agents
        intent = request.intent
        resume_model = self._resolve_resume_data(request, context)
        resume_data = (
            resume_model.model_dump(exclude_none=True)
            if resume_model is not None
            else {}
        )
        job_description = request.jobDescription or ""
        message_history = request.messageHistory or []
        
        # Build input text based on intent and available data
        input_data = self._build_agent_input(intent, resume_data, job_description, message_history, request.audioData)
        
        # Log orchestration start
        logger.log_orchestration_start(str(input_data) if isinstance(input_data, bytes) else input_data, session_id, user_id)
        
        try:
            # Map intent to agent sequence directly
            agent_sequence = self._map_intent_to_agents(intent)
            
            logger.log_intent_analysis(input_text, agent_sequence, "intent_based", session_id)
            
            state: OrchestrationState = {
                "original_input": input_data,
                "current_input": input_data,
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
            
            return current_response
            
        except Exception as e:
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
        
        agent_start_time = time.time()
        try:
            response = agent.process(current_input, context)
            agent_execution_time = time.time() - agent_start_time
            
            # Log successful agent execution
            logger.log_agent_execution_complete(agent_name, response, session_id, agent_execution_time)
            
        except Exception as e:
            agent_execution_time = time.time() - agent_start_time
            logger.log_agent_error(agent_name, e, session_id)
            raise

        trace = list(context.decision_trace or [])
        trace.append(f"Orchestrator: Routed to {agent_name} based on intent analysis.")
        response.decision_trace = trace

        audited_response = self.governance.audit(response, current_input)
        context.add_to_history(audited_response)
        context.decision_trace = trace
        
        logger.debug("Governance audit completed", session_id=session_id, agent_name=agent_name, governance_passed=True)

        next_input = current_input
        if current_index < len(agent_sequence) - 1:
            next_input = self._build_chained_input(
                state["original_input"],
                audited_response,
                agent_name,
            )
            logger.debug("Built chained input for next agent", session_id=session_id, next_agent_index=current_index + 1, chained_input_length=len(next_input))

        return {
            "original_input": state["original_input"],
            "current_input": next_input,
            "context": context,
            "agent_sequence": agent_sequence,
            "current_index": current_index + 1,
            "current_response": audited_response,
        }

    @staticmethod
    def _route_next_step(state: OrchestrationState) -> str:
        if state["current_index"] >= len(state["agent_sequence"]):
            return "end"
        return "continue"

    def _analyze_intent(self, input_text: str, context: SessionContext) -> list[str]:
        session_id = getattr(context, 'session_id', 'unknown')
        
        if not input_text or not input_text.strip():
            logger.debug("Empty input detected, defaulting to ResumeCriticAgent", session_id=session_id)
            return ["ResumeCriticAgent"]

        lower_input = input_text.lower()
        
        # Log keyword-based intent analysis
        logger.debug("Starting keyword-based intent analysis", session_id=session_id, input_length=len(input_text))

        if any(
            keyword in lower_input
            for keyword in (
                "skill",
                "strength",
                "phrasing",
                "achievement",
                "evidence",
                "improve my resume",
            )
        ):
            logger.debug("Intent matched: ContentStrengthAgent (keywords)", session_id=session_id, keywords_matched=["skill", "strength", "phrasing", "achievement", "evidence", "improve my resume"])
            return ["ContentStrengthAgent"]

        if any(
            keyword in lower_input
            for keyword in ("interview", "mock", "behavioral", "practice")
        ):
            logger.debug("Intent matched: InterviewCoachAgent (keywords)", session_id=session_id, keywords_matched=["interview", "mock", "behavioral", "practice"])
            return ["InterviewCoachAgent"]

        if any(keyword in lower_input for keyword in ("job", "alignment", "match", "gap")):
            logger.debug("Intent matched: JobAlignmentAgent (keywords)", session_id=session_id, keywords_matched=["job", "alignment", "match", "gap"])
            return ["JobAlignmentAgent"]

        if any(
            keyword in lower_input
            for keyword in ("analyze", "critique", "review", "feedback")
        ):
            if not context.history:
                logger.debug("Intent matched: ResumeCriticAgent -> ContentStrengthAgent (keywords, no history)", session_id=session_id, keywords_matched=["analyze", "critique", "review", "feedback"], has_history=False)
                return ["ResumeCriticAgent", "ContentStrengthAgent"]
            logger.debug("Intent matched: ResumeCriticAgent (keywords, has history)", session_id=session_id, keywords_matched=["analyze", "critique", "review", "feedback"], has_history=True, history_length=len(context.history))
            return ["ResumeCriticAgent"]

        logger.debug("No keyword matches, falling back to LLM intent analysis", session_id=session_id)
        return self._analyze_intent_with_llm(input_text, context)

    def _analyze_intent_with_llm(
        self,
        input_text: str,
        context: SessionContext,
    ) -> list[str]:
        session_id = getattr(context, 'session_id', 'unknown')
        
        if self.intent_gemini_service is None:
            logger.warning("No intent Gemini service available, defaulting to ResumeCriticAgent", session_id=session_id)
            return ["ResumeCriticAgent"]

        try:
            context_summary = (
                "No previous interactions"
                if not context.history
                else f"{len(context.history)} previous agent interactions"
            )

            prompt_text = self.INTENT_ANALYSIS_PROMPT % (input_text, context_summary)
            
            logger.log_api_call("gemini", "intent_analysis", session_id, prompt_length=len(prompt_text))
            
            llm_start_time = time.time()
            response = self.intent_gemini_service.generate_response(
                system_prompt=(
                    "You are an intent classifier. Respond with ONLY a JSON array "
                    "of agent names."
                ),
                user_input=prompt_text,
                context=None,
            )
            llm_execution_time = time.time() - llm_start_time
            
            logger.debug("LLM intent analysis completed", session_id=session_id, execution_time_ms=round(llm_execution_time * 1000, 2), response_length=len(response))
            
            result = self._parse_agent_sequence(response)
            logger.log_intent_analysis(input_text, result, "llm_based", session_id)
            
            return result
            
        except Exception as e:
            logger.log_agent_error("IntentAnalysisLLM", e, session_id)
            logger.warning("LLM intent analysis failed, defaulting to ResumeCriticAgent", session_id=session_id)
            return ["ResumeCriticAgent"]

    def _parse_agent_sequence(self, response: str) -> list[str]:
        session_id = "unknown"  # We don't have session context here
        
        logger.debug("Parsing agent sequence from LLM response", session_id=session_id, raw_response=response[:200])
        
        cleaned_response = response.strip()
        json_array_match = re.search(r"\[[\s\S]*\]", cleaned_response)
        if json_array_match:
            cleaned_response = json_array_match.group()
            logger.debug("Found JSON array in response", session_id=session_id, extracted_json=cleaned_response)

        try:
            parsed = json.loads(cleaned_response)
            if isinstance(parsed, list):
                candidates = [str(item) for item in parsed]
                logger.debug("Successfully parsed JSON array", session_id=session_id, parsed_agents=candidates)
            else:
                candidates = []
                logger.warning("Parsed JSON was not a list", session_id=session_id, parsed_type=type(parsed).__name__)
        except json.JSONDecodeError as e:
            logger.warning("JSON decode failed, falling back to string parsing", session_id=session_id, error=str(e))
            cleaned_response = cleaned_response.strip("[]")
            candidates = [item.strip().strip("\"'") for item in cleaned_response.split(",")]
            logger.debug("Parsed using string split method", session_id=session_id, split_candidates=candidates)

        valid_agents = [
            candidate for candidate in candidates if self._is_valid_agent(candidate)
        ]
        
        if not valid_agents:
            logger.warning("No valid agents found in parsed response, defaulting to ResumeCriticAgent", session_id=session_id, invalid_candidates=candidates, available_agents=list(self.agents.keys()))
            return ["ResumeCriticAgent"]
        
        logger.debug("Valid agents identified", session_id=session_id, valid_agents=valid_agents)
        return valid_agents

    def _is_valid_agent(self, agent_name: str) -> bool:
        return agent_name in self.agents

    @staticmethod
    def _build_chained_input(
        original_input: str,
        previous_response: AgentResponse,
        previous_agent: str,
    ) -> str:
        prior_content = previous_response.content or ""
        return (
            f"Original request: {original_input}\n\n"
            f"Previous analysis from {previous_agent}:\n"
            f"{prior_content}\n\n"
            "Continue analysis based on the above context."
        )

    def _build_agent_input(self, intent: str, resume_data: dict, job_description: str, message_history: list, audio_data: Optional[bytes] = None) -> Union[str, bytes]:
        """Build input text for agents based on intent and available data."""
        if audio_data is not None and intent == "INTERVIEW_COACH":
            # For interview coaching with audio, return the audio data directly
            return audio_data
        
        if intent == "RESUME_CRITIC":
            return f"Analyze this resume: {json.dumps(resume_data, indent=2)}"
        
        elif intent == "CONTENT_STRENGTH":
            return f"Analyze the content strength and skills of this resume using STAR/XYZ methodology: {json.dumps(resume_data, indent=2)}"
        
        elif intent == "ALIGNMENT":
            return f"Analyze the fit between this resume and the Job Description. Use Google Search to research the company or specific technology trends if necessary.\nResume: {json.dumps(resume_data, indent=2)}\nJD: {job_description}"
        
        elif intent == "INTERVIEW_COACH":
            history_str = json.dumps([{"role": msg.role, "text": msg.text} for msg in message_history], indent=2)
            return f"You are a high-stakes Interview Coach. Based on this alignment data: {job_description}, conduct a realistic mock interview. Ask one targeted question at a time. History: {history_str}"
        
        else:
            # Fallback
            return f"Process this request: {json.dumps(resume_data, indent=2)}"

    def _resolve_resume_data(self, request: ChatRequest, context: SessionContext) -> Resume | None:
        """Resolve resume input with strict precedence: resumeData first, then resumeFile."""
        session_id = getattr(context, "session_id", "unknown")
        if request.resumeData is not None:
            if self._has_resume_content(request.resumeData):
                logger.debug(
                    "Orchestrator using resumeData payload",
                    session_id=session_id,
                    source="resumeData",
                )
                self._store_resume_in_context(request.resumeData, context)
                return request.resumeData
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
            resume = self._extract_resume_from_file(request.resumeFile.model_dump(), context)
            self._store_resume_in_context(resume, context)
            return resume

        memory_resume = self._resume_from_context(context)
        if memory_resume is not None:
            logger.debug(
                "Orchestrator using resume from shared session memory",
                session_id=session_id,
                source="shared_memory",
            )
            return memory_resume

        logger.debug("No resume input provided in request", session_id=session_id)
        return None

    def _extract_resume_from_file(
        self, resume_file_payload: dict[str, Any], context: SessionContext
    ) -> Resume:
        extractor = self.agents.get("ExtractorAgent")
        if extractor is None:
            raise RuntimeError("ExtractorAgent is required when resumeFile is provided.")

        response = extractor.process(json.dumps(resume_file_payload), context)
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
        
        return intent_mapping.get(intent, ["ResumeCriticAgent"])
