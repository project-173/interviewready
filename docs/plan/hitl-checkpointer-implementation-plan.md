HITL + Checkpointer Implementation Plan

Purpose
Provide a minimal, teachable implementation plan for adding human-in-the-loop (HITL) review and checkpoint-based time travel to the agent flow.

Goals
1. Pause execution when confidence is low or validation fails.
2. Allow users to resume or rewind to a prior step.
3. Persist graph state per session so “go back” is real, not a re-run.
4. Keep the changes scoped and demo-friendly for a school project.

Non-Goals
1. Full production-grade durability or distributed checkpointers.
2. Advanced role-based access, approvals, or multi-user workflows.
3. Replacing the current frontend intent selector in one step.

Assumptions
1. The existing flow is driven by `ChatRequest.intent`.
2. The extractor is currently run before the LangGraph loop.
3. Session state is currently stored in-memory (`SessionStore`).
4. Only one active user per session id is required for the demo.

Current System Summary
1. `OrchestrationAgent` builds a simple LangGraph loop with `run_agent`.
2. Resume normalization and extraction occur in `_normalize_or_fail`.
3. No checkpointer is wired into the orchestration graph.
4. “Go back” is currently a frontend-only pattern using new intents.

Proposed Architecture
1. Move resume extraction into the LangGraph flow as a `normalize` node.
2. Introduce a `HITL_REVIEW` checkpoint when:
   a. Extractor confidence is below threshold.
   b. Validation errors exist.
3. Add a checkpointer (LangGraph `MemorySaver`) keyed by `session_id`.
4. Add API controls to resume or rewind from checkpoints.

Workflow Graph (New)
1. `normalize` node
2. Conditional edge:
   a. `needs_review` -> `HITL_REVIEW` interrupt
   b. else -> `run_agent`
3. `run_agent` node (existing)
4. End
5. Resume path:
   a. `HITL_REVIEW` -> `normalize`
6. Normalize behavior on resume:
   a. If `normalized_resume` exists -> skip extraction.
   b. Else -> run extractor.
   c. Always run validation and recompute `needs_review`.

Minimal State Additions
1. Extend `OrchestrationState` to include:
   a. `checkpoint_id` (optional)
   b. `needs_review` (bool)
   c. `review_payload` (structured data for UI)
   d. `shared_memory` (dict) as a single source of truth for demo
2. Avoid out-of-band mutation in `SessionContext.shared_memory` for demo.
3. Suggested `review_payload` shape:
   a. `extracted_data`
   b. `validation_errors`
   c. `confidence_score`
   d. `fields_requiring_attention`

API Contract Changes
1. Add optional fields to `ChatRequest`:
   a. `control` with values like `resume`, `rewind`
   b. `checkpoint_id` for explicit time travel
   c. `resume_data` (structured resume edits from HITL)
2. Return checkpoint metadata in `ChatApiResponse.metadata`:
   a. `checkpoint_id`
   b. `review_required`
   c. `review_payload`
3. Control semantics:
   a. `resume` without `checkpoint_id` uses latest checkpoint.
   b. `rewind` requires explicit `checkpoint_id`.
   c. Invalid `checkpoint_id` returns 400 with clear error.
4. Input precedence:
   a. If `resume_data` present -> use it and skip extraction.
   b. Else if `resume_file` present -> run extraction.

HITL Review Flow
1. User uploads resume.
2. `normalize` runs extractor and validates.
3. If `needs_review`:
   a. Graph interrupts and returns `review_payload`.
   b. Frontend shows extracted data for confirmation or edits.
4. User submits corrections with `control=resume`.
5. On resume:
   a. Incoming payload replaces `normalized_resume`.
   b. Validation is re-run inside `normalize`.
   c. `needs_review` is recomputed.
6. Graph continues to `run_agent`.
7. Optional demo safety:
   a. `max_review_attempts` (e.g., 2 or 3).
   b. If exceeded -> return hard error or force proceed.

Checkpoint Strategy (Demo-Grade)
1. Use LangGraph `MemorySaver` for in-memory checkpoints.
2. Key checkpoints by `session_id`.
3. Support rewind by setting `checkpoint_id` on request.
4. Rewind behavior:
   a. Truncate all checkpoints after selected `checkpoint_id`.
   b. Resume execution from that point (no branching).
5. Rewind semantics:
   a. Discard current in-memory state on rewind.
   b. Load state strictly from the checkpoint.

Suggested File Touches
1. `backend/app/orchestration/orchestration_agent.py`
2. `backend/app/orchestration/persistence.py`
3. `backend/app/orchestration/state_mapper.py`
3. `backend/app/models/agent.py`
4. `backend/app/api/v1/endpoints/chat.py`
5. `backend/app/api/v1/services.py`
6. `frontend/backendService.ts`
7. `frontend/App.tsx` or relevant workflow UI

Testing Plan
1. Unit test: extractor low confidence triggers interrupt.
2. Unit test: resumeData bypasses extractor.
3. Unit test: resumeFile + confidence ok continues to agent.
4. Unit test: rewind restores previous checkpoint.
5. Integration test: end-to-end HITL review.
6. Must-have unit test: resume edits on resume flow clear review state and proceed.
7. Rewind integrity test: after rewind, state matches checkpoint exactly and `run_agent` has not executed.

Risks and Mitigations
1. Risk: “time travel” looks like re-run.
   Mitigation: return checkpoint ids and show in UI.
2. Risk: shared memory drift across rewinds.
   Mitigation: treat checkpoint state as source of truth for demo.
3. Risk: session store in-memory only.
   Mitigation: document as demo-only limitation.
4. Risk: frontend and backend “go back” semantics diverge.
   Mitigation: document the difference and show in demo.

Deliverables for the Project
1. Working HITL review step in the resume flow.
2. Checkpoint resume and rewind demo.
3. Short README section describing architecture and tradeoffs.
4. “Go back” comparison table for grading clarity.

Milestone Breakdown
1. Wire checkpointer + interrupt (backend only).
2. Ensure resume + rewind state correctness with tests.
3. Expose control and checkpoint metadata (API).
4. Frontend review UX for extracted resume.
5. Add demo script and finalize tests.
