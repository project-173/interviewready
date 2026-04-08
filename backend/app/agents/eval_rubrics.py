"""Per-agent judge rubrics and thresholds."""

from __future__ import annotations

from typing import Dict
from pydantic import BaseModel

JUDGE_TEMPERATURE = 0.0

BASE_RUBRIC = """Evaluate the agent output for a resume coaching application.
Focus on correctness, usefulness, and clarity of feedback based only on the provided input."""

AGENT_RUBRICS: Dict[str, str] = {
    "ResumeCriticAgent": (
        "Score structure, clarity, ATS compliance, and actionable critique. "
        "Penalize missing or vague issue descriptions."
    ),
    "ContentStrengthAgent": (
        "Score evidence strength, quantification, and missing impact. "
        "Penalize suggestions that add unsupported claims."
    ),
    "JobAlignmentAgent": (
        "Score alignment to job requirements, precision of missing keywords, "
        "and grounding to the JD text."
    ),
    "InterviewCoachAgent": (
        "Score question relevance, progression across the interview, and "
        "coherence with message history."
    ),
}


class EvalThresholds(BaseModel):
    min_quality_score: float
    min_accuracy_score: float
    min_helpfulness_score: float


EVAL_THRESHOLDS: Dict[str, EvalThresholds] = {
    "ResumeCriticAgent": EvalThresholds(
        min_quality_score=0.7,
        min_accuracy_score=0.8,
        min_helpfulness_score=0.7,
    ),
    "ContentStrengthAgent": EvalThresholds(
        min_quality_score=0.7,
        min_accuracy_score=0.7,
        min_helpfulness_score=0.8,
    ),
    "JobAlignmentAgent": EvalThresholds(
        min_quality_score=0.7,
        min_accuracy_score=0.8,
        min_helpfulness_score=0.7,
    ),
    "InterviewCoachAgent": EvalThresholds(
        min_quality_score=0.7,
        min_accuracy_score=0.7,
        min_helpfulness_score=0.8,
    ),
}


def get_rubric(agent_name: str) -> str:
    return AGENT_RUBRICS.get(agent_name, BASE_RUBRIC)


def get_thresholds(agent_name: str) -> EvalThresholds:
    return EVAL_THRESHOLDS.get(
        agent_name, EvalThresholds(0.7, 0.7, 0.7)
    )
