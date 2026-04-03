"""Helpers for managing Langfuse datasets defined in evals/datasets-new."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

from pydantic import BaseModel, Field

from evals.loader import DATASET_DIR, ResolvedEvalCase, load_eval_cases

DATASET_SPECS_DIR = Path(__file__).resolve().parent / "datasets-new"


class DatasetSpec(BaseModel):
    schema_version: int = 1
    dataset_name: str
    agent: str
    edge_cases: bool = False
    case_ids: List[str] = Field(default_factory=list)


def load_dataset_specs(specs_dir: Path = DATASET_SPECS_DIR) -> Dict[str, DatasetSpec]:
    if not specs_dir.exists():
        raise FileNotFoundError(f"Dataset spec directory not found: {specs_dir}")

    specs: Dict[str, DatasetSpec] = {}
    for path in sorted(specs_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        spec = DatasetSpec.model_validate(data)
        if spec.dataset_name in specs:
            raise ValueError(f"Duplicate dataset name: {spec.dataset_name}")
        specs[spec.dataset_name] = spec
    return specs


def load_cases_for_spec(spec: DatasetSpec) -> List[ResolvedEvalCase]:
    cases = load_eval_cases(DATASET_DIR, edge_cases=spec.edge_cases)
    case_map = {case.id: case for case in cases}
    missing = [case_id for case_id in spec.case_ids if case_id not in case_map]
    if missing:
        raise ValueError(
            "Dataset spec references unknown case ids: " + ", ".join(missing)
        )

    selected = [case_map[case_id] for case_id in spec.case_ids]
    mismatched = [case.id for case in selected if case.agent != spec.agent]
    if mismatched:
        raise ValueError(
            f"Dataset spec agent mismatch for {spec.dataset_name}: "
            + ", ".join(mismatched)
        )
    return selected


def build_case_payload(case: ResolvedEvalCase) -> Dict[str, object]:
    return {
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


def sync_langfuse_dataset(*, langfuse, spec: DatasetSpec, cases: List[ResolvedEvalCase]) -> None:
    try:
        langfuse.create_dataset(
            name=spec.dataset_name,
            description="InterviewReady LLM judge eval cases",
            metadata={
                "source": "local_fixtures",
                "agent": spec.agent,
                "edge_cases": spec.edge_cases,
            },
        )
        print(f"Created Langfuse dataset: {spec.dataset_name}")
    except Exception as exc:
        print(f"Langfuse dataset create skipped ({spec.dataset_name}): {exc}")

    for case in cases:
        payload = build_case_payload(case)
        try:
            langfuse.create_dataset_item(
                dataset_name=spec.dataset_name,
                input={"case_id": case.id, "case": payload},
                metadata={"case_id": case.id, "agent": case.agent},
                id=f"{spec.dataset_name}:{case.id}",
            )
        except Exception as exc:
            print(f"Langfuse item create skipped ({case.id}): {exc}")

    print(
        f"Uploaded {len(cases)} items to Langfuse dataset '{spec.dataset_name}'"
    )


def sync_langfuse_datasets(
    *, langfuse, specs: Iterable[DatasetSpec]
) -> None:
    for spec in specs:
        cases = load_cases_for_spec(spec)
        sync_langfuse_dataset(langfuse=langfuse, spec=spec, cases=cases)
