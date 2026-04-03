"""Run Langfuse-backed eval experiments for datasets in evals/datasets-new."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, Optional

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

from langfuse import Langfuse

from app.agents import GeminiService
from app.agents.llm_judge import LLmasJudgeEvaluator
from app.core.config import settings
from evals.langfuse_datasets import load_cases_for_spec, load_dataset_specs
from evals.run_evals import _build_batch_run_name, _case_id_from_item, _run_experiment


def run_experiment(dataset_name: str, *, run_name: Optional[str] = None):
    specs = load_dataset_specs()
    if dataset_name not in specs:
        raise ValueError(f"Unknown dataset name: {dataset_name}")

    if not settings.LANGFUSE_PUBLIC_KEY:
        raise RuntimeError("LANGFUSE_PUBLIC_KEY is not set.")

    spec = specs[dataset_name]
    cases = load_cases_for_spec(spec)

    langfuse = Langfuse()
    gemini_service = GeminiService(api_key=settings.GEMINI_API_KEY)
    judge = LLmasJudgeEvaluator(gemini_service)

    dataset = langfuse.get_dataset(spec.dataset_name)
    base_run_name = _build_batch_run_name(run_name)
    run_name_full = f"{base_run_name}/{spec.dataset_name}"

    result = _run_experiment(
        cases=cases,
        langfuse=langfuse,
        judge=judge,
        gemini_service=gemini_service,
        run_name=run_name_full,
        dataset=dataset,
    )
    return result


def run_all_experiments(*, run_name: Optional[str] = None) -> Dict[str, object]:
    results: Dict[str, object] = {}
    specs = load_dataset_specs()
    for dataset_name in specs:
        results[dataset_name] = run_experiment(dataset_name, run_name=run_name)
    return results


def _print_summary(result) -> None:
    print("\nSummary")
    print(f"Cases run: {len(result.item_results)}")
    failures = [r for r in result.item_results if not r.evaluations]
    print(f"Failures: {len(failures)}")
    for item_result in result.item_results:
        case_id = _case_id_from_item(item_result.item)
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Langfuse dataset experiments defined in evals/datasets-new"
    )
    parser.add_argument(
        "--dataset",
        help="Dataset name to run (default: run all datasets)",
    )
    parser.add_argument("--run-name", help="Override run name")
    args = parser.parse_args()

    if args.dataset:
        result = run_experiment(args.dataset, run_name=args.run_name)
        _print_summary(result)
        return

    results = run_all_experiments(run_name=args.run_name)
    for dataset_name, result in results.items():
        print(f"\n=== {dataset_name} ===")
        _print_summary(result)


if __name__ == "__main__":
    main()
