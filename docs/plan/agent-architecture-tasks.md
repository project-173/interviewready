# Implementation Plan: Agent Architecture Fixes

Date: 2026-03-14
Status: Draft (no code changes yet)

## Scope
Address intent routing split-brain, add a minimal Normalize->Analyze pipeline, preserve current agents, and introduce structured artifacts. No tool integrations or ATS scoring in this phase.

## Assumptions
- `ChatRequest.intent` is the source of truth for routing.
- We keep `InterviewCoachAgent` as a one-shot analysis agent unless a separate interview loop is explicitly requested.
- LLM intent classification is removed for determinism.

## Tasks (ordered)

### 0) Alignment / Contract Checks
- Confirm frontend sends only supported intent values.
- Decide allowed intents and enforce them in `ChatRequest`.

Files:
- `backend/app/models/agent.py`
- `frontend/backendService.ts` (if it maps intent values)

Tests:
- `backend/tests/test_api_endpoints.py`

### 0.5) Add Missing Model Definitions
- Add model types needed by the pipeline:
  - `ResumeDocument` (lite)
  - `AnalysisArtifact`
  - `ActionPlan`
  - Optional: `NormalizationFailure` (if modeled explicitly)
- Decide file placement (existing `backend/app/models/agent.py` vs new module).
- Export new models in `backend/app/models/__init__.py`.

Files:
- `backend/app/models/agent.py` (or new `backend/app/models/resume_document.py`)
- `backend/app/models/__init__.py`

### 1) Enforce Intent Enum + Deterministic Routing
- Change `ChatRequest.intent` to `Literal["RESUME_CRITIC", "CONTENT_STRENGTH", "ALIGNMENT", "INTERVIEW_COACH"]` (or Enum) for validation.
- Update tests to cover invalid intent values.

Files:
- `backend/app/models/agent.py`
- `backend/tests/test_api_endpoints.py`

### 1.5) Use `_map_intent_to_agents()` Directly
- Replace `_analyze_intent` usage with `_map_intent_to_agents`.
- Delete `_analyze_intent` and `_analyze_intent_with_llm` unless a new `user_message` field is introduced.
- Remove unused Gemini intent service wiring if no longer needed.

Files:
- `backend/app/orchestration/orchestration_agent.py`
- `backend/app/api/v1/services.py`

### 2) Introduce Minimal ResumeDocument (Lite)
- Add `ResumeDocument` model:
  - `id`, `source`, `raw_text`, `parse_confidence`, `warnings`
  - Optional `sections` + `spans` for future evidence linkage
- Update Extractor path to produce `ResumeDocument` (or embed into OrchestrationState) without breaking existing outputs.

Files:
- `backend/app/models/resume.py` (or new `backend/app/models/resume_document.py`)
- `backend/app/agents/extractor.py`
- `backend/app/orchestration/orchestration_agent.py`

Tests:
- `backend/tests/test_resume_input_priority.py`

### 3) Normalize Stage (Explicit)
- Add a Normalize step that produces ResumeDocument or a normalization failure result.
- If normalization fails, short-circuit and return ActionPlan with recovery steps.
- Keep extraction logic but move it into a named stage for logging and governance visibility.

Files:
- `backend/app/orchestration/orchestration_agent.py`
- `backend/app/models/agent.py` (ActionPlan type)

Tests:
- Add tests for normalization failure path.

### 4a) Store Structured Artifacts in OrchestrationState
- Add `artifacts: list[AnalysisArtifact]` to state.
- Store each agent’s structured result separately (no chained text blobs).

Files:
- `backend/app/orchestration/orchestration_agent.py`
- `backend/app/models/agent.py` (AnalysisArtifact)

Tests:
- `backend/tests/test_orchestration_governance.py`

### 4b) Remove Chained Text Inputs
- Remove `_build_chained_input` usage in favor of passing structured state.
- Ensure all agents read from normalized state or the artifact list.

Files:
- `backend/app/orchestration/orchestration_agent.py`

Tests:
- `backend/tests/test_orchestration_governance.py`

### 5) Governance Hooks (Bounded)
- Keep governance audit per artifact.
- Optionally add a single retry for parse failures with strict budget (if required).
- Log governance outcomes into ActionPlan metadata.

Files:
- `backend/app/governance/sharp_governance_service.py`
- `backend/app/orchestration/orchestration_agent.py`

Tests:
- Extend `backend/tests/test_orchestration_governance.py`.

## Out of Scope (Explicit)
- ATS scoring integration
- Web search/tools integration
- InterviewCoachAgent subgraph / multi-turn loop
- Persistent session storage

## Risks
- Stricter intent validation can break clients that send unexpected values.
- Refactoring orchestration state may require updates to multiple tests.

## Validation Plan
- Run backend tests:
  - `backend/tests/test_api_endpoints.py`
  - `backend/tests/test_resume_input_priority.py`
  - `backend/tests/test_orchestration_governance.py`

## Exit Criteria
- Intent routing is deterministic and validated.
- Normalize->Analyze pipeline runs end-to-end.
- Governance metadata preserved.
