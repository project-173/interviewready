"""Per-agent evaluation tests using LLM-as-a-judge."""

from __future__ import annotations

import sys
import warnings
from datetime import date
from pathlib import Path
from typing import Dict, Type

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.loader import build_agent_input, build_input_summary, build_session_context, load_eval_cases
from app.agents import (
    ContentStrengthAgent,
    InterviewCoachAgent,
    JobAlignmentAgent,
    ResumeCriticAgent,
    GeminiService,
)
from app.agents.eval_rubrics import get_thresholds
from app.agents.llm_judge import LLmasJudgeEvaluator
from app.core.config import settings

SKIP_EVAL_TESTS = settings.SKIP_EVAL_TESTS

AGENT_CLASSES: Dict[str, Type] = {
    "ResumeCriticAgent": ResumeCriticAgent,
    "ContentStrengthAgent": ContentStrengthAgent,
    "JobAlignmentAgent": JobAlignmentAgent,
    "InterviewCoachAgent": InterviewCoachAgent,
}

EVAL_CASES = load_eval_cases()


def _is_judge_failure(evaluation) -> bool:
    concerns = [c.lower() for c in (evaluation.concerns or [])]
    if "parse error" in concerns or "judge evaluation unavailable" in concerns:
        return True
    reason = (evaluation.reasoning or "").lower()
    return reason.startswith("failed to parse") or reason.startswith("evaluation failed")


def _assert_threshold(metric: str, score: float, threshold: float, reasoning: str) -> None:
    if score < threshold - 0.1:
        pytest.fail(
            f"{metric} score {score:.2f} below hard threshold {threshold - 0.1:.2f}. "
            f"Reasoning: {reasoning}"
        )
    if score < threshold:
        warnings.warn(
            f"{metric} score {score:.2f} below soft threshold {threshold:.2f}. "
            f"Reasoning: {reasoning}",
            stacklevel=2,
        )


@pytest.fixture(scope="class")
def gemini_service():
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        pytest.skip("GEMINI_API_KEY not set")
    return GeminiService(api_key=api_key)


@pytest.fixture(scope="class")
def judge_evaluator(gemini_service):
    return LLmasJudgeEvaluator(gemini_service)


@pytest.mark.eval
@pytest.mark.skipif(SKIP_EVAL_TESTS, reason="Eval tests disabled in CI/CD")
@pytest.mark.parametrize("case", EVAL_CASES, ids=[case.id for case in EVAL_CASES])
def test_agent_evaluations(case, judge_evaluator, gemini_service) -> None:
    agent_class = AGENT_CLASSES[case.agent]
    agent = agent_class(gemini_service)
    input_data = build_agent_input(case)
    context = build_session_context(case, session_id=f"pytest-{case.id}")

    response = agent.process(input_data, context)
    assert response.content, f"{case.agent} returned empty content"

    run_name = f"pytest/{case.agent}/{date.today().isoformat()}"
    evaluation = judge_evaluator.evaluate(
        agent_name=case.agent,
        input_data=build_input_summary(case),
        output=response.content or "",
        intent=case.intent,
        session_id=context.session_id,
        message_history=case.message_history,
        run_name=run_name,
    )

    if _is_judge_failure(evaluation):
        evaluation = judge_evaluator.evaluate(
            agent_name=case.agent,
            input_data=build_input_summary(case),
            output=response.content or "",
            intent=case.intent,
            session_id=context.session_id,
            message_history=case.message_history,
            run_name=run_name,
        )

    if _is_judge_failure(evaluation):
        pytest.skip("Judge returned malformed response")

    thresholds = get_thresholds(case.agent)
    _assert_threshold(
        "quality",
        evaluation.quality_score,
        thresholds.min_quality_score,
        evaluation.reasoning,
    )
    _assert_threshold(
        "accuracy",
        evaluation.accuracy_score,
        thresholds.min_accuracy_score,
        evaluation.reasoning,
    )
    _assert_threshold(
        "helpfulness",
        evaluation.helpfulness_score,
        thresholds.min_helpfulness_score,
        evaluation.reasoning,
    )
