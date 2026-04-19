"""Agent registry and construction helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.agents.content_strength import ContentStrengthAgent
from app.agents.extractor import ExtractorAgent
from app.agents.interview_coach import InterviewCoachAgent
from app.agents.job_alignment import JobAlignmentAgent
from app.agents.resume_critic import ResumeCriticAgent

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.agents.base import BaseAgentProtocol


class AgentRegistry:
    """Construct agents from configurable names."""

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[object], BaseAgentProtocol]] = {
            "ExtractorAgent": ExtractorAgent,
            "ResumeCriticAgent": ResumeCriticAgent,
            "ContentStrengthAgent": ContentStrengthAgent,
            "JobAlignmentAgent": JobAlignmentAgent,
            "InterviewCoachAgent": InterviewCoachAgent,
        }

    def configured_names(self) -> list[str]:
        """Return normalized agent names from configuration."""
        raw = "ExtractorAgent,ResumeCriticAgent,ContentStrengthAgent,JobAlignmentAgent,InterviewCoachAgent"
        names = [part.strip() for part in raw.split(",") if part.strip()]
        return names or list(self._factories.keys())

    def build_agents(self, gemini_service: object) -> list[BaseAgentProtocol]:
        """Instantiate configured agents in order."""
        agents: list[BaseAgentProtocol] = []
        for name in self.configured_names():
            factory = self._factories.get(name)
            if factory is None:
                available = ", ".join(sorted(self._factories.keys()))
                msg = f"Unknown agent in AGENT_PIPELINE: {name}. Available: {available}"
                raise ValueError(msg)
            agents.append(factory(gemini_service))
        return agents
