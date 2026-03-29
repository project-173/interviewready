"""Dataset loader and helpers for LLM-as-judge evaluations."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, Field

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if BACKEND_DIR.exists() and str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models import AgentInput, InterviewMessage, Resume, SessionContext

DATASET_DIR = Path(__file__).resolve().parent / "datasets"


class ResumeFixture(BaseModel):
    id: str
    title: str
    notes: str
    last_reviewed: date
    resume: Resume


class JobDescriptionFixture(BaseModel):
    id: str
    title: str
    notes: str
    last_reviewed: date
    requirements: List[str] = Field(default_factory=list)
    text: str


class HistoryFixture(BaseModel):
    id: str
    title: str
    notes: str
    last_reviewed: date
    messages: List[InterviewMessage] = Field(default_factory=list)


class EvalCase(BaseModel):
    id: str
    agent: str
    intent: str
    resume_id: str
    job_description_id: Optional[str] = None
    history_id: Optional[str] = None
    notes: str
    tags: List[str] = Field(default_factory=list)
    edge_case: bool = False
    context_shared_memory: Optional[Dict[str, Any]] = None


class ResumeFixtureFile(BaseModel):
    schema_version: int = 1
    fixtures: List[ResumeFixture]


class JobDescriptionFixtureFile(BaseModel):
    schema_version: int = 1
    fixtures: List[JobDescriptionFixture]


class HistoryFixtureFile(BaseModel):
    schema_version: int = 1
    fixtures: List[HistoryFixture]


class EvalCasesFile(BaseModel):
    schema_version: int = 1
    cases: List[EvalCase]


class ResolvedEvalCase(BaseModel):
    id: str
    agent: str
    intent: str
    resume: Resume
    job_description: str
    job_requirements: List[str]
    message_history: List[InterviewMessage]
    notes: str
    tags: List[str]
    edge_case: bool
    context_shared_memory: Optional[Dict[str, Any]] = None
    fixture_ids: Dict[str, Optional[str]] = Field(default_factory=dict)


class EvalFixtures(BaseModel):
    resumes: Dict[str, ResumeFixture]
    job_descriptions: Dict[str, JobDescriptionFixture]
    histories: Dict[str, HistoryFixture]
    cases: List[EvalCase]


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_fixtures(dataset_dir: Path, edge_cases: bool = False) -> EvalFixtures:
    if edge_cases:
        resumes_path = dataset_dir / "edge_case_resumes.json"
        jobs_path = dataset_dir / "edge_case_jobs.json"
        histories_path = dataset_dir / "edge_case_histories.json"
        cases_path = dataset_dir / "edge_case_cases.json"
    else:
        resumes_path = dataset_dir / "resumes.json"
        jobs_path = dataset_dir / "job_descriptions.json"
        histories_path = dataset_dir / "histories.json"
        cases_path = dataset_dir / "cases.json"

    resumes = ResumeFixtureFile.model_validate(_load_json(resumes_path)).fixtures
    job_descriptions = JobDescriptionFixtureFile.model_validate(
        _load_json(jobs_path)
    ).fixtures
    histories = HistoryFixtureFile.model_validate(
        _load_json(histories_path)
    ).fixtures
    cases = EvalCasesFile.model_validate(_load_json(cases_path)).cases

    return EvalFixtures(
        resumes={fixture.id: fixture for fixture in resumes},
        job_descriptions={fixture.id: fixture for fixture in job_descriptions},
        histories={fixture.id: fixture for fixture in histories},
        cases=cases,
    )


def load_eval_cases(dataset_dir: Path = DATASET_DIR, edge_cases: bool = False) -> List[ResolvedEvalCase]:
    fixtures = _load_fixtures(dataset_dir, edge_cases)
    resolved_cases: List[ResolvedEvalCase] = []

    for case in fixtures.cases:
        resume_fixture = fixtures.resumes.get(case.resume_id)
        if resume_fixture is None:
            raise ValueError(f"Unknown resume_id '{case.resume_id}' for case {case.id}")

        job_fixture = (
            fixtures.job_descriptions.get(case.job_description_id)
            if case.job_description_id
            else None
        )
        history_fixture = (
            fixtures.histories.get(case.history_id) if case.history_id else None
        )

        resolved_cases.append(
            ResolvedEvalCase(
                id=case.id,
                agent=case.agent,
                intent=case.intent,
                resume=resume_fixture.resume,
                job_description=job_fixture.text if job_fixture else "",
                job_requirements=job_fixture.requirements if job_fixture else [],
                message_history=history_fixture.messages if history_fixture else [],
                notes=case.notes,
                tags=case.tags,
                edge_case=case.edge_case,
                context_shared_memory=case.context_shared_memory,
                fixture_ids={
                    "resume_id": case.resume_id,
                    "job_description_id": case.job_description_id,
                    "history_id": case.history_id,
                },
            )
        )

    return resolved_cases


def build_agent_input(case: ResolvedEvalCase) -> AgentInput:
    return AgentInput(
        intent=case.intent,
        resume=case.resume,
        job_description=case.job_description,
        message_history=case.message_history,
    )


def build_session_context(
    case: ResolvedEvalCase,
    *,
    session_id: str = "eval-session",
    user_id: str = "eval-runner",
) -> SessionContext:
    context = SessionContext(
        session_id=session_id,
        user_id=user_id,
        resume_data=None,
        job_description=case.job_description or None,
    )
    if case.context_shared_memory:
        context.shared_memory = dict(case.context_shared_memory)
    return context


def build_input_summary(case: ResolvedEvalCase, max_history: int = 6) -> str:
    parts = [
        f"Intent: {case.intent}",
        f"Agent: {case.agent}",
    ]
    if case.job_description:
        parts.append(f"Job Description: {case.job_description[:400]}")
    if case.message_history:
        parts.append("Message History (most recent first):")
        for message in list(reversed(case.message_history))[:max_history]:
            role = getattr(message, "role", None) or "unknown"
            text = getattr(message, "text", None) or ""
            parts.append(f"- {role}: {text[:240]}")
    return "\n".join(parts)


def filter_cases(
    cases: Iterable[ResolvedEvalCase],
    *,
    agents: Optional[List[str]] = None,
    include_tags: Optional[List[str]] = None,
) -> List[ResolvedEvalCase]:
    selected: List[ResolvedEvalCase] = []
    for case in cases:
        if agents and case.agent not in agents:
            continue
        if include_tags and not any(tag in case.tags for tag in include_tags):
            continue
        selected.append(case)
    return selected


def find_stale_fixtures(
    dataset_dir: Path = DATASET_DIR, *, max_age_days: int = 60
) -> List[str]:
    fixtures = _load_fixtures(dataset_dir)
    cutoff = date.today().toordinal() - max_age_days
    stale: List[str] = []

    def _check(name: str, last_reviewed: date) -> None:
        if last_reviewed.toordinal() < cutoff:
            stale.append(f"{name} (last_reviewed={last_reviewed.isoformat()})")

    for fixture in fixtures.resumes.values():
        _check(f"resume:{fixture.id}", fixture.last_reviewed)
    for fixture in fixtures.job_descriptions.values():
        _check(f"job_description:{fixture.id}", fixture.last_reviewed)
    for fixture in fixtures.histories.values():
        _check(f"history:{fixture.id}", fixture.last_reviewed)

    return stale
