"""Structural checks for agent outputs (non-judge, always-on)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Tuple, Type

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.loader import build_agent_input, build_session_context, filter_cases, load_eval_cases
from app.agents import (
    ContentStrengthAgent,
    InterviewCoachAgent,
    JobAlignmentAgent,
    ResumeCriticAgent,
    GeminiService,
)
from app.core.config import settings
from app.models import AlignmentReport, ContentStrengthReport, ResumeCriticReport
from app.utils.json_parser import parse_json_payload

AGENT_CLASSES: Dict[str, Type] = {
    "ResumeCriticAgent": ResumeCriticAgent,
    "ContentStrengthAgent": ContentStrengthAgent,
    "JobAlignmentAgent": JobAlignmentAgent,
    "InterviewCoachAgent": InterviewCoachAgent,
}

JSON_MODELS: Dict[str, Type] = {
    "ResumeCriticAgent": ResumeCriticReport,
    "ContentStrengthAgent": ContentStrengthReport,
    "JobAlignmentAgent": AlignmentReport,
}

LENGTH_BOUNDS: Dict[str, Tuple[int, int]] = {
    "ResumeCriticAgent": (200, 9000),
    "ContentStrengthAgent": (200, 9000),
    "JobAlignmentAgent": (100, 4000),
    "InterviewCoachAgent": (40, 6000),
}


STRUCTURAL_CASES = filter_cases(load_eval_cases(), include_tags=["structural"])


@pytest.mark.parametrize(
    "case",
    STRUCTURAL_CASES,
    ids=[case.id for case in STRUCTURAL_CASES],
)
def test_agent_structural_checks(case) -> None:
    """Validate schema, non-empty output, and length bounds."""
    gemini_service = GeminiService(api_key=settings.GEMINI_API_KEY)
    agent_class = AGENT_CLASSES[case.agent]
    agent = agent_class(gemini_service)

    input_data = build_agent_input(case)
    context = build_session_context(case)
    response = agent.process(input_data, context)

    assert response.content, f"{case.agent} returned empty content"
    output = response.content.strip()
    assert output, f"{case.agent} returned blank content"

    min_len, max_len = LENGTH_BOUNDS[case.agent]
    assert min_len <= len(output) <= max_len, (
        f"{case.agent} output length {len(output)} outside bounds "
        f"{min_len}-{max_len}"
    )

    if case.agent in JSON_MODELS:
        parsed = parse_json_payload(output, allow_array=False)
        assert isinstance(parsed, dict), f"{case.agent} returned invalid JSON"
        JSON_MODELS[case.agent].model_validate(parsed)
    elif case.agent == "InterviewCoachAgent":
        parsed = parse_json_payload(output, allow_array=False)
        assert isinstance(parsed, dict), "InterviewCoachAgent returned invalid JSON"
        assert (
            "current_question_number" in parsed
            or parsed.get("interview_complete", False)
        ), "InterviewCoachAgent response missing interview state"
