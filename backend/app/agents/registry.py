"""Agent registry and construction helpers."""

from __future__ import annotations

from collections.abc import Callable

from app.agents.base import BaseAgentProtocol
from app.agents.content_strength import ContentStrengthAgent
from app.agents.extractor import ExtractorAgent
from app.agents.edit_plan import EditPlanAgent
from app.agents.interview_coach import InterviewCoachAgent
from app.agents.job_alignment import JobAlignmentAgent
from app.agents.resume_critic import ResumeCriticAgent
from app.core.config import settings


class AgentRegistry:
    """Construct agents from configurable names."""

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[object], BaseAgentProtocol]] = {
            "ExtractorAgent": lambda gemini_service: ExtractorAgent(gemini_service),
            "EditPlanAgent": lambda gemini_service: EditPlanAgent(gemini_service),
            "ResumeCriticAgent": lambda gemini_service: ResumeCriticAgent(gemini_service),
            "ContentStrengthAgent": lambda gemini_service: ContentStrengthAgent(gemini_service),
            "JobAlignmentAgent": lambda gemini_service: JobAlignmentAgent(gemini_service),
            "InterviewCoachAgent": lambda gemini_service: InterviewCoachAgent(gemini_service),
        }

    def configured_names(self) -> list[str]:
        """Return normalized agent names from configuration."""
        raw = "ExtractorAgent,EditPlanAgent,ResumeCriticAgent,ContentStrengthAgent,JobAlignmentAgent,InterviewCoachAgent"
        names = [part.strip() for part in raw.split(",") if part.strip()]
        return names or list(self._factories.keys())

    def build_agents(self, gemini_service: object) -> list[BaseAgentProtocol]:
        """Instantiate configured agents in order."""
        agents: list[BaseAgentProtocol] = []
        for name in self.configured_names():
            factory = self._factories.get(name)
            if factory is None:
                available = ", ".join(sorted(self._factories.keys()))
                raise ValueError(
                    f"Unknown agent in AGENT_PIPELINE: {name}. Available: {available}"
                )
            agents.append(factory(gemini_service))
        return agents
