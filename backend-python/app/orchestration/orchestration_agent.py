"""LangGraph-based orchestration service for routing across agents."""

from __future__ import annotations

import json
import re
from typing import Any
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents.base import BaseAgentProtocol
from app.agents.gemini_service import GeminiService
from app.governance.sharp_governance_service import SharpGovernanceService
from app.models.agent import AgentResponse
from app.models.session import SessionContext


class OrchestrationState(TypedDict):
    """Workflow state used by LangGraph orchestration."""

    original_input: str
    current_input: str
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

    def orchestrate(self, input_text: str, context: SessionContext) -> AgentResponse:
        """Run intent analysis and execute selected agent sequence."""
        agent_sequence = self._analyze_intent(input_text, context)
        if not agent_sequence:
            agent_sequence = ["ResumeCriticAgent"]

        state: OrchestrationState = {
            "original_input": input_text,
            "current_input": input_text,
            "context": context,
            "agent_sequence": agent_sequence,
            "current_index": 0,
            "current_response": None,
        }
        result = self.workflow.invoke(state)
        current_response = result.get("current_response")
        if current_response is None:
            raise RuntimeError("Orchestration completed without an agent response.")
        return current_response

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

        if current_index >= len(agent_sequence):
            return state

        agent_name = agent_sequence[current_index]
        agent = self.agents.get(agent_name)
        if agent is None:
            available = ", ".join(sorted(self.agents.keys()))
            raise RuntimeError(
                f"No agent found for target: {agent_name}. Available agents: {available}"
            )

        current_input = state["current_input"]
        response = agent.process(current_input, context)

        trace = list(context.decision_trace or [])
        trace.append(f"Orchestrator: Routed to {agent_name} based on intent analysis.")
        response.decision_trace = trace

        audited_response = self.governance.audit(response, current_input)
        context.add_to_history(audited_response)
        context.decision_trace = trace

        next_input = current_input
        if current_index < len(agent_sequence) - 1:
            next_input = self._build_chained_input(
                state["original_input"],
                audited_response,
                agent_name,
            )

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
        if not input_text or not input_text.strip():
            return ["ResumeCriticAgent"]

        lower_input = input_text.lower()

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
            return ["ContentStrengthAgent"]

        if any(
            keyword in lower_input
            for keyword in ("interview", "mock", "behavioral", "practice")
        ):
            return ["InterviewCoachAgent"]

        if any(keyword in lower_input for keyword in ("job", "alignment", "match", "gap")):
            return ["JobAlignmentAgent"]

        if any(
            keyword in lower_input
            for keyword in ("analyze", "critique", "review", "feedback")
        ):
            if not context.history:
                return ["ResumeCriticAgent", "ContentStrengthAgent"]
            return ["ResumeCriticAgent"]

        return self._analyze_intent_with_llm(input_text, context)

    def _analyze_intent_with_llm(
        self,
        input_text: str,
        context: SessionContext,
    ) -> list[str]:
        if self.intent_gemini_service is None:
            return ["ResumeCriticAgent"]

        try:
            context_summary = (
                "No previous interactions"
                if not context.history
                else f"{len(context.history)} previous agent interactions"
            )

            prompt_text = self.INTENT_ANALYSIS_PROMPT % (input_text, context_summary)
            response = self.intent_gemini_service.generate_response(
                system_prompt=(
                    "You are an intent classifier. Respond with ONLY a JSON array "
                    "of agent names."
                ),
                user_input=prompt_text,
                context=None,
            )
            return self._parse_agent_sequence(response)
        except Exception:  # noqa: BLE001
            return ["ResumeCriticAgent"]

    def _parse_agent_sequence(self, response: str) -> list[str]:
        cleaned_response = response.strip()
        json_array_match = re.search(r"\[[\s\S]*\]", cleaned_response)
        if json_array_match:
            cleaned_response = json_array_match.group()

        try:
            parsed = json.loads(cleaned_response)
            if isinstance(parsed, list):
                candidates = [str(item) for item in parsed]
            else:
                candidates = []
        except json.JSONDecodeError:
            cleaned_response = cleaned_response.strip("[]")
            candidates = [item.strip().strip("\"'") for item in cleaned_response.split(",")]

        valid_agents = [
            candidate for candidate in candidates if self._is_valid_agent(candidate)
        ]
        return valid_agents or ["ResumeCriticAgent"]

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
