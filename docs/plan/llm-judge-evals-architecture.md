# Implementation Plan: LLM-Judge Evals Architecture

Date: 2026-03-27
Status: Draft (no code changes yet)

## Goal
Align live evals, script-based evals, and tests around a single evaluator (`LLmasJudgeEvaluator`) so scores are consistent and easy to maintain.

## Architecture Summary
- `backend/app/agents/llm_judge.py` is the shared evaluator (prompt + parse + scoring + Langfuse logging).
- `backend/app/api/v1/endpoints/chat.py` runs live evals (per request, non-blocking).
- `evals/run_evals.py` runs batch evals on curated datasets (periodic).
- `backend/tests/test_agent_evals.py` runs per-agent regression tests (local/CI).

## Tasks (ordered)

### 1) Structural checks first (cheap CI coverage)
Ship lightweight, deterministic checks immediately to keep CI meaningful during the rest of the work.

Actions:
- Add schema validity, non-empty output, and per-agent length bounds checks.
- These checks always run in CI (ignore any judge-test skip flags).

Files:
- `backend/tests/test_agent_structural_checks.py` (new)

### 2) Decide fixture source of truth + implement loader (blocking)
Resolve whether tests load from datasets or use inline fixtures, then implement the loader.

Decision:
- Adopt `evals/datasets/*.json` as the single source for both `pytest` and `run_evals.py` (decision locked).

Actions:
- Build a loader that deserializes JSON into Pydantic models.
- Share loader with `run_evals.py` to avoid duplicate parsing logic.

Files:
- `backend/tests/test_agent_evals.py`
- `evals/run_evals.py`

### 3) Define dataset fixtures (single source of truth)
Specify the dataset content and diversity requirements.

Actions:
- Add 4-5 resume fixtures covering:
  - Strong SWE resume
  - Sparse resume with weak metrics
  - Employment gap
  - Career changer
  - Overqualified senior
- Add 4 JD fixtures with explicit, checkable requirements.
- Add 3 history fixtures at T1, T5, T10 for InterviewCoachAgent.
- Document the intent of each fixture and the failure mode it targets.
- Add `last_reviewed` date to each fixture for drift tracking.
- Target a max N cases per agent; retire superseded cases when adding new ones.

Files:
- `evals/datasets/*.json`
- `evals/README.md` (new)

### 4) Standardize evaluator usage (refactor)
Unify the existing evaluator interface without changing live behavior.

Actions:
- Ensure `LLmasJudgeEvaluator.evaluate(...)` accepts optional `trace_id`, `intent`, `session_id`.
- Confirm metadata is logged consistently.
- Set judge temperature to 0 for determinism.

### 5) Script-based eval runner (working serial)
Ship a minimal `evals/` runner to enable coverage quickly.

Actions:
- Create `evals/run_evals.py` that loads datasets and calls `LLmasJudgeEvaluator`.
- Emit results to console and (optionally) Langfuse if trace IDs are provided.
- Add `--run-name` and consistent run naming.
- Handle agent call failures: mark case failed, log error, continue run.

Files:
- `evals/run_evals.py`
- `evals/datasets/*.json`

### 6) Calibration run (before rubrics + thresholds)
Run the judge on all fixtures with the existing generic rubric to observe real outputs.

Actions:
- Collect raw scores and reasoning.
- Identify rubric gaps and surprising failures.
- Set judge temperature to 0 for calibration runs.

### 7) Per-agent judge rubrics (after calibration)
Replace generic rubrics with agent-specific scoring criteria based on calibration.

Actions:
- ResumeCriticAgent: structure, clarity, ATS compliance.
- ContentStrengthAgent: evidence strength, quantification, missing impact.
- JobAlignmentAgent: JD grounding check and missing keyword precision.
- InterviewCoachAgent: history coherence and question progression.
- Include message history in judge context for InterviewCoachAgent.
- Consider moving rubrics + thresholds into `backend/app/agents/eval_rubrics.py` and importing from `llm_judge.py` as it grows.

Files:
- `backend/app/agents/llm_judge.py` (prompt/rubric home)

### 8) Threshold calibration
Set per-agent thresholds based on observed score distributions.

Actions:
- Define thresholds after reviewing calibration outputs.
- Store thresholds alongside rubrics.
- Retire or migrate `EVAL_SCORE_THRESHOLDS` in `backend/app/core/constants.py` to avoid two sources of truth.

### 9) Per-agent eval tests (judge-based)
Add deterministic tests for each agent with a minimum score threshold.

Actions:
- Create/extend `backend/tests/test_agent_evals.py`.
- Store per-agent thresholds alongside rubrics to avoid drift.
- On judge parse failures, skip the test with a clear reason (do not mark agent as failing).
- Retry judge parse failures once before skipping.
- Set judge temperature to 0 for test runs.
- Add soft failure mode: warn if score < threshold; fail only if score < threshold - 0.1.
- Respect `SKIP_EVAL_TESTS` or equivalent flag for judge-based tests only.

Files:
- `backend/tests/test_agent_evals.py`
- `backend/app/agents/llm_judge.py` (thresholds + rubrics)

### 10) Script runner optimizations (later)
Add performance and reporting improvements after baseline coverage works.

Actions:
- Implement parallel execution (use `concurrent.futures.ThreadPoolExecutor` if the Gemini SDK is synchronous; `asyncio.gather` only if async).
- Warn on stale fixtures using `last_reviewed` (e.g., >60 days).
- Log token usage / estimated cost per run.
- Estimate runtime from dataset size and log expected duration.

### 11) Live eval integration (feature)
Rewire the chat endpoint to use the standardized evaluator interface.

Actions:
- Guard behind `settings.LANGFUSE_LLM_AS_A_JUDGE_ENABLED`.
- Add `settings.EVAL_SAMPLE_RATE` and only judge a fraction of requests.
- Build a compact input summary for the judge (intent + JD snippet).
- Pass message history to the judge for InterviewCoachAgent scoring in live evals.
- Capture trace ID from Langfuse if available.
- Run evaluation asynchronously to avoid latency spikes (thread executor if judge is sync).
- Rollback: if p95 latency increases by >500ms over baseline, disable `LANGFUSE_LLM_AS_A_JUDGE_ENABLED`.

Files:
- `backend/app/api/v1/endpoints/chat.py`
- `backend/app/core/config.py`
- `backend/app/agents/llm_judge.py`

## Out of Scope
- Full evaluation orchestration framework
- Multi-judge ensembles
- Production gating based on judge scores

## Risks
- LLM judge variability can make tests flaky without stable inputs.
- Dataset drift if not refreshed regularly.

## Dataset Drift Mitigation
- The person running `evals/run_evals.py` is responsible for reviewing fixtures.
- Add `last_reviewed` to each fixture and warn if >60 days.
- Add new cases when production traces surface unexpected failures.

## Production Trace Promotion
- Define a lightweight workflow in `evals/README.md`:
  - Capture trace IDs with notable failures.
  - Convert into fixtures within 1 week.
  - Tag fixture with the originating trace ID.

## Judge Failure Handling
Explicitly separate judge failures from agent failures.

Guideline:
```
try:
    scores = parse_judge_response(raw)
except Exception:
    pytest.skip("Judge returned malformed response")
```
## Run Naming Strategy
Use a consistent naming format so Langfuse comparisons are meaningful.

Proposed format:
- `evals/{agent}/{dataset_version}/{date}` for batch runs
- `live/{agent}/{intent}/{date}` for sampled live evals

Store the run name in Langfuse metadata and in any local eval logs.
Define `dataset_version` as a semver in `evals/README.md` and bump it when fixtures change.


## Validation Plan
- Task 1: `backend/tests/test_agent_structural_checks.py` passes in CI.
- Task 3: Each fixture file includes `notes` and `last_reviewed`.
- Task 5: `evals/run_evals.py --agent job_alignment --run-name test` completes; Langfuse shows all three judge scores.
- Task 6: Calibration is complete when rubric gaps are documented and at least one threshold is revised from observed outputs.
- Task 9: `pytest -m eval` passes with at least one edge case per agent.
- Task 11: Local integration run with `EVAL_SAMPLE_RATE=1.0` logs scores on the Langfuse trace.

## Exit Criteria
- Live evals, batch evals, and tests all use the same evaluator.
- Each agent is tested against at least 4 fixture combinations, including one edge case.
- Batch eval script runs in under 10 minutes with parallelism (Task 10), or the dataset size is reduced to meet the target after runtime estimation.
