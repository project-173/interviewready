"""Batch eval runner for LLM-as-judge evaluations."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if BACKEND_DIR.exists() and str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(BACKEND_DIR / ".env")
except Exception as exc:
    print(f"Warning: failed to load .env files: {exc}")

from app.agents import (
    ContentStrengthAgent,
    InterviewCoachAgent,
    JobAlignmentAgent,
    ResumeCriticAgent,
    GeminiService,
)
from app.agents.llm_judge import LLmasJudgeEvaluator
from app.core.config import settings
from evals.loader import (
    DATASET_DIR,
    ResolvedEvalCase,
    build_agent_input,
    build_input_summary,
    build_session_context,
    filter_cases,
    find_stale_fixtures,
    load_eval_cases,
)

AGENT_CLASSES = {
    "ResumeCriticAgent": ResumeCriticAgent,
    "ContentStrengthAgent": ContentStrengthAgent,
    "JobAlignmentAgent": JobAlignmentAgent,
    "InterviewCoachAgent": InterviewCoachAgent,
}


def _read_dataset_version() -> str:
    readme_path = REPO_ROOT / "evals" / "README.md"
    if not readme_path.exists():
        return "unknown"
    for line in readme_path.read_text(encoding="utf-8").splitlines():
        if line.lower().startswith("dataset version"):
            parts = line.split("`")
            if len(parts) >= 2:
                return parts[1].strip()
    return "unknown"


def _build_run_name(agent: str, explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    dataset_version = _read_dataset_version()
    today = dt.date.today().isoformat()
    return f"evals/{agent}/{dataset_version}/{today}"


def _build_batch_run_name(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    dataset_version = _read_dataset_version()
    today = dt.date.today().isoformat()
    return f"evals/batch/{dataset_version}/{today}"


def _parse_agents(raw: Optional[str]) -> Optional[List[str]]:
    if not raw:
        return None
    agents = [item.strip() for item in raw.split(",") if item.strip()]
    return agents or None


def _get_item_input(item: Any) -> Any:
    if isinstance(item, dict):
        return item.get("input", item)
    if hasattr(item, "input"):
        return item.input
    return None


def _case_id_from_item(item: Any) -> Optional[str]:
    if isinstance(item, dict):
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        input_data = item.get("input") if isinstance(item.get("input"), dict) else {}
        return (
            metadata.get("case_id")
            or input_data.get("case_id")
            or input_data.get("id")
        )
    if hasattr(item, "metadata") and isinstance(item.metadata, dict):
        return item.metadata.get("case_id") or item.metadata.get("id")
    if hasattr(item, "input") and isinstance(item.input, dict):
        return item.input.get("case_id") or item.input.get("id")
    return None


def _resolve_case_from_item(
    item: Any, case_map: Dict[str, ResolvedEvalCase]
) -> ResolvedEvalCase:
    input_data = _get_item_input(item)
    if not isinstance(input_data, dict):
        raise ValueError("Dataset item input must be a dict")

    case_id = input_data.get("case_id") or input_data.get("id")
    if case_id and case_id in case_map:
        return case_map[case_id]

    case_payload = (
        input_data.get("case") if isinstance(input_data.get("case"), dict) else input_data
    )
    if "resume_id" in case_payload and "resume" not in case_payload:
        raise ValueError(
            "Dataset item references resume_id without a full resume. "
            "Provide case_id to use local fixtures or include resume data."
        )

    resolved_payload = {
        "id": case_payload.get("id")
        or case_payload.get("case_id")
        or case_id
        or getattr(item, "id", "dataset-item"),
        "agent": case_payload.get("agent"),
        "intent": case_payload.get("intent"),
        "resume": case_payload.get("resume"),
        "job_description": case_payload.get("job_description", ""),
        "job_requirements": case_payload.get("job_requirements", []),
        "message_history": case_payload.get("message_history", []),
        "notes": case_payload.get("notes", ""),
        "tags": case_payload.get("tags", []),
        "edge_case": case_payload.get("edge_case", False),
        "context_shared_memory": case_payload.get("context_shared_memory"),
        "fixture_ids": case_payload.get("fixture_ids", {}),
    }

    return ResolvedEvalCase.model_validate(resolved_payload)


def _run_manual(
    *,
    cases,
    judge,
    gemini_service,
    trace_id: Optional[str],
    run_name_override: Optional[str],
) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    for case in cases:
        agent_class = AGENT_CLASSES.get(case.agent)
        if agent_class is None:
            print(f"Skipping unknown agent: {case.agent}")
            continue

        agent = agent_class(gemini_service)
        input_data = build_agent_input(case)
        context = build_session_context(case)
        run_name = _build_run_name(case.agent, run_name_override)

        try:
            response = agent.process(input_data, context)
        except Exception as exc:
            print(f"[FAIL] {case.id} agent_error={exc}")
            results.append({"case": case.id, "status": "agent_error", "error": str(exc)})
            continue

        evaluation = judge.evaluate(
            agent_name=case.agent,
            input_data=build_input_summary(case),
            output=response.content or "",
            trace_id=trace_id,
            intent=case.intent,
            session_id=context.session_id,
            message_history=case.message_history,
            run_name=run_name,
        )

        print(
            f"[OK] {case.id} "
            f"quality={evaluation.quality_score:.2f} "
            f"accuracy={evaluation.accuracy_score:.2f} "
            f"helpfulness={evaluation.helpfulness_score:.2f}"
        )
        results.append({"case": case.id, "status": "ok"})
    return results


def _run_experiment(
    *,
    cases,
    langfuse,
    judge,
    gemini_service,
    run_name: str,
) -> Any:
    from langfuse.experiment import Evaluation

    case_map = {case.id: case for case in cases}
    data = []
    for case in cases:
        data.append(
            {
                "input": {
                    "case_id": case.id,
                    "agent": case.agent,
                    "intent": case.intent,
                    "input_summary": build_input_summary(case),
                },
                "metadata": {
                    "case_id": case.id,
                    "agent": case.agent,
                    "intent": case.intent,
                    "tags": case.tags,
                    "edge_case": case.edge_case,
                    "fixture_ids": case.fixture_ids,
                },
            }
        )

    def task(*, item, **kwargs):
        metadata = item.get("metadata") if isinstance(item, dict) else None
        case_id = None
        if metadata:
            case_id = metadata.get("case_id")
        if not case_id and isinstance(item, dict):
            case_id = item.get("input", {}).get("case_id")
        if not case_id or case_id not in case_map:
            raise ValueError("Missing case_id for experiment item")

        case = case_map[case_id]
        agent_class = AGENT_CLASSES[case.agent]
        agent = agent_class(gemini_service)
        input_data = build_agent_input(case)
        context = build_session_context(case)

        response = agent.process(input_data, context)
        return {
            "case_id": case.id,
            "agent": case.agent,
            "intent": case.intent,
            "session_id": context.session_id,
            "message_history": case.message_history,
            "input_summary": build_input_summary(case),
            "output": response.content or "",
        }

    def evaluator(*, input, output, expected_output=None, metadata=None, **kwargs):
        try:
            per_agent_run_name = _build_run_name(
                output.get("agent", "unknown"), None
            )
            evaluation = judge.evaluate(
                agent_name=output.get("agent", "unknown"),
                input_data=output.get("input_summary", ""),
                output=output.get("output", ""),
                trace_id=None,
                intent=output.get("intent"),
                session_id=output.get("session_id"),
                message_history=output.get("message_history"),
                run_name=per_agent_run_name,
            )
            reason = (evaluation.reasoning or "")[:200]
            meta = {
                "case_id": output.get("case_id"),
                "agent": output.get("agent"),
            }
            return [
                Evaluation(
                    name="judge_quality_score",
                    value=evaluation.quality_score,
                    comment=reason,
                    metadata={**meta, "batch_run_name": run_name},
                ),
                Evaluation(
                    name="judge_accuracy_score",
                    value=evaluation.accuracy_score,
                    comment=reason,
                    metadata={**meta, "batch_run_name": run_name},
                ),
                Evaluation(
                    name="judge_helpfulness_score",
                    value=evaluation.helpfulness_score,
                    comment=reason,
                    metadata={**meta, "batch_run_name": run_name},
                ),
            ]
        except Exception as exc:
            return Evaluation(
                name="judge_eval_error",
                value=0,
                comment=str(exc),
                metadata={"case_id": output.get("case_id")},
            )

    return langfuse.run_experiment(
        name="LLM Judge Eval",
        run_name=run_name,
        description="Offline LLM-as-judge batch evaluation run",
        data=data,
        task=task,
        evaluators=[evaluator],
        max_concurrency=1,
        metadata={
            "dataset_version": _read_dataset_version(),
            "case_count": len(cases),
        },
    )


def _run_experiment_dataset(
    *,
    dataset,
    case_map: Dict[str, ResolvedEvalCase],
    langfuse,
    judge,
    gemini_service,
    run_name: str,
) -> Any:
    from langfuse.experiment import Evaluation

    def task(*, item, **kwargs):
        case = _resolve_case_from_item(item, case_map)
        agent_class = AGENT_CLASSES[case.agent]
        agent = agent_class(gemini_service)
        input_data = build_agent_input(case)
        context = build_session_context(case)

        response = agent.process(input_data, context)
        return {
            "case_id": case.id,
            "agent": case.agent,
            "intent": case.intent,
            "session_id": context.session_id,
            "message_history": case.message_history,
            "input_summary": build_input_summary(case),
            "output": response.content or "",
        }

    def evaluator(*, input, output, expected_output=None, metadata=None, **kwargs):
        try:
            per_agent_run_name = _build_run_name(output.get("agent", "unknown"), None)
            evaluation = judge.evaluate(
                agent_name=output.get("agent", "unknown"),
                input_data=output.get("input_summary", ""),
                output=output.get("output", ""),
                trace_id=None,
                intent=output.get("intent"),
                session_id=output.get("session_id"),
                message_history=output.get("message_history"),
                run_name=per_agent_run_name,
            )
            reason = (evaluation.reasoning or "")[:200]
            meta = {
                "case_id": output.get("case_id"),
                "agent": output.get("agent"),
                "batch_run_name": run_name,
            }
            return [
                Evaluation(
                    name="judge_quality_score",
                    value=evaluation.quality_score,
                    comment=reason,
                    metadata=meta,
                ),
                Evaluation(
                    name="judge_accuracy_score",
                    value=evaluation.accuracy_score,
                    comment=reason,
                    metadata=meta,
                ),
                Evaluation(
                    name="judge_helpfulness_score",
                    value=evaluation.helpfulness_score,
                    comment=reason,
                    metadata=meta,
                ),
            ]
        except Exception as exc:
            return Evaluation(
                name="judge_eval_error",
                value=0,
                comment=str(exc),
                metadata={"case_id": output.get("case_id")},
            )

    return dataset.run_experiment(
        name="LLM Judge Eval",
        run_name=run_name,
        description="Offline LLM-as-judge batch evaluation run",
        task=task,
        evaluators=[evaluator],
        max_concurrency=1,
        metadata={
            "dataset_version": _read_dataset_version(),
        },
    )


def _sync_langfuse_dataset(
    *,
    langfuse,
    dataset_name: str,
    cases,
) -> None:
    try:
        langfuse.create_dataset(
            name=dataset_name,
            description="InterviewReady LLM judge eval cases",
            metadata={"source": "local_fixtures"},
        )
        print(f"Created Langfuse dataset: {dataset_name}")
    except Exception as exc:
        print(f"Langfuse dataset create skipped: {exc}")

    for case in cases:
        payload = {
            "id": case.id,
            "agent": case.agent,
            "intent": case.intent,
            "resume": case.resume.model_dump(),
            "job_description": case.job_description,
            "job_requirements": case.job_requirements,
            "message_history": [m.model_dump() for m in case.message_history],
            "notes": case.notes,
            "tags": case.tags,
            "edge_case": case.edge_case,
            "context_shared_memory": case.context_shared_memory,
            "fixture_ids": case.fixture_ids,
        }
        dataset_item_id = f"{dataset_name}:{case.id}"
        langfuse.create_dataset_item(
            dataset_name=dataset_name,
            input={"case_id": case.id, "case": payload},
            metadata={"case_id": case.id, "agent": case.agent},
            id=dataset_item_id,
        )
    print(f"Uploaded {len(cases)} items to Langfuse dataset '{dataset_name}'")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LLM-as-judge evals")
    parser.add_argument("--agent", help="Comma-separated agent names to run")
    parser.add_argument("--run-name", help="Override run name for Langfuse")
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--trace-id", help="Optional Langfuse trace ID")
    parser.add_argument("--warn-stale-days", type=int, default=60)
    parser.add_argument("--langfuse-dataset", help="Langfuse dataset name")
    args = parser.parse_args()

    agents_filter = _parse_agents(args.agent)
    cases = load_eval_cases(DATASET_DIR)
    cases = filter_cases(cases, agents=agents_filter)
    if args.max_cases:
        cases = cases[: args.max_cases]

    stale = find_stale_fixtures(DATASET_DIR, max_age_days=args.warn_stale_days)
    if stale:
        print("Warning: stale fixtures detected")
        for item in stale:
            print(f" - {item}")

    if not settings.LANGFUSE_PUBLIC_KEY:
        print(
            "Warning: LANGFUSE_PUBLIC_KEY is not set. "
            "Langfuse logging will be disabled."
        )

    gemini_service = GeminiService(api_key=settings.GEMINI_API_KEY)
    judge = LLmasJudgeEvaluator(gemini_service)

    if args.trace_id:
        results = _run_manual(
            cases=cases,
            judge=judge,
            gemini_service=gemini_service,
            trace_id=args.trace_id,
            run_name_override=args.run_name,
        )
        print("\nSummary")
        print(f"Cases run: {len(results)}")
        failures = [r for r in results if r["status"] != "ok"]
        print(f"Failures: {len(failures)}")
        if failures:
            for failure in failures:
                print(f" - {failure['case']}: {failure['status']}")
        print(f"Langfuse trace: {args.trace_id}")
        return

    if settings.LANGFUSE_PUBLIC_KEY:
        try:
            from langfuse import Langfuse

            langfuse = Langfuse()
            batch_run_name = _build_batch_run_name(args.run_name)
            case_map = {case.id: case for case in cases}
            if args.langfuse_dataset:
                dataset = langfuse.get_dataset(args.langfuse_dataset)
                result = _run_experiment_dataset(
                    dataset=dataset,
                    case_map=case_map,
                    langfuse=langfuse,
                    judge=judge,
                    gemini_service=gemini_service,
                    run_name=batch_run_name,
                )
            else:
                result = _run_experiment(
                    cases=cases,
                    langfuse=langfuse,
                    judge=judge,
                    gemini_service=gemini_service,
                    run_name=batch_run_name,
                )

            print("\nSummary")
            print(f"Cases run: {len(result.item_results)}")
            failures = [
                r for r in result.item_results if not r.evaluations
            ]
            print(f"Failures: {len(failures)}")
            for item_result in result.item_results:
                item = item_result.item
                case_id = _case_id_from_item(item)
                evals = {e.name: e.value for e in item_result.evaluations}
                if evals:
                    print(
                        f"[OK] {case_id} "
                        f"quality={evals.get('judge_quality_score', 0):.2f} "
                        f"accuracy={evals.get('judge_accuracy_score', 0):.2f} "
                        f"helpfulness={evals.get('judge_helpfulness_score', 0):.2f}"
                    )
                else:
                    print(f"[FAIL] {case_id} no evaluations")

            # Backfill trace-level scores using experiment evaluations
            for item_result in result.item_results:
                if not item_result.trace_id:
                    continue
                for evaluation in item_result.evaluations:
                    try:
                        langfuse.create_score(
                            name=evaluation.name,
                            value=evaluation.value,
                            trace_id=item_result.trace_id,
                            metadata=evaluation.metadata,
                        )
                    except Exception as exc:
                        print(
                            "Failed to attach score to trace "
                            f"{item_result.trace_id}: {exc}"
                        )

            if result.dataset_run_url:
                print(f"Langfuse experiment: {result.dataset_run_url}")
            return
        except Exception as exc:
            print(f"Langfuse experiment run failed: {exc}")

    results = _run_manual(
        cases=cases,
        judge=judge,
        gemini_service=gemini_service,
        trace_id=None,
        run_name_override=args.run_name,
    )
    print("\nSummary")
    print(f"Cases run: {len(results)}")
    failures = [r for r in results if r["status"] != "ok"]
    print(f"Failures: {len(failures)}")
    if failures:
        for failure in failures:
            print(f" - {failure['case']}: {failure['status']}")


if __name__ == "__main__":
    main()
