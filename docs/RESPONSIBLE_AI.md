# Explainable and Responsible AI Report -- InterviewReady

## 1. Introduction

This report documents how Explainable AI (XAI) and Responsible AI (RAI) principles have been considered, embedded, and operationalised throughout the InterviewReady system. It covers the core analysis agents, the enhanced InterviewCoachAgent, the new GeminiLive voice interview path, and the LLM-as-a-judge evaluation layer introduced in the `sit` branch. Each pipeline stage is mapped to specific principles and controls.

Principles addressed:

| Principle | Abbreviation |
|-----------|-------------|
| Fairness & Bias Mitigation | F |
| Transparency & Explainability | T |
| Human Oversight & Control | H |
| Privacy & Data Minimisation | P |
| Robustness & Safety | R |
| Accountability | A |
| Governance | G |

---

## 2. Fairness & Bias Mitigation

### 2.1 Identified Bias Risks

| Bias Type | Risk Description | Applicable Agent |
|-----------|-----------------|-----------------|
| **Representational bias** | LLM trained on Western career corpora may penalise non-Western resume formats | ResumeCriticAgent |
| **Keyword bias** | JobAlignmentAgent may over-fit to JD keywords and under-weight equivalent skills | JobAlignmentAgent |
| **Confidence inflation** | ContentStrengthAgent may assign higher evidence strength to quantified achievements, disadvantaging entry-level candidates | ContentStrengthAgent |
| **Interview question bias** | InterviewCoachAgent may generate questions culturally specific to certain regions | InterviewCoachAgent |
| **Age / gender / nationality bias in questions** | Generated questions may encode demographic assumptions | InterviewCoachAgent |
| **Confidence scoring disparity** | ExtractorAgent confidence may be lower for non-Western date formats or unconventional resume structures | ExtractorAgent |

### 2.2 Mitigations Implemented

**ContentStrengthAgent -- faithfulness constraint:**
```
NEVER invent new skills, achievements, or experiences.
NEVER imply greater scope or seniority than the original supports.
If a suggestion requires fabrication, omit it entirely.
```

**InterviewCoachAgent -- `BIAS_PATTERNS` regex detection (new in `sit` branch):**
```python
BIAS_PATTERNS = {
    "age":         r"\b(young|recent graduate|digital native|energetic)\b",
    "gender":      r"\b(he|she|him|her|male|female|manpower)\b",
    "nationality": r"\b(native english|american-born|citizens only)\b",
}
```
When a bias pattern is detected in user input or generated output, `sharp_metadata["bias_review_required"] = True` is set, triggering the SHARP governance `_validate_interview_coach_agent()` check which flags `bias_review_required` and `requires_human_review`.

**SHARP governance -- unfaithful suggestion flagging:**
Suggestions that cannot be made without fabrication are surfaced to the user for HITL review before any edit is applied.

**Confidence threshold enforcement:**
Responses with `confidence_score < 0.3` are flagged as `low_confidence`, preventing low-quality (potentially biased) outputs from reaching users silently.

**Prompt versioning via Langfuse:**
All system prompts are tracked. Drift in prompt content that might introduce new bias is detectable by comparing prompt versions in the Langfuse dashboard.

### 2.3 Future Recommendations

- Implement a diverse test-resume benchmark spanning multiple nationalities, education levels, and experience domains.
- Extend `BIAS_PATTERNS` to cover additional demographic markers and regional phrasing.
- Add configurable cultural context (e.g., resume region) as an input parameter to the analysis agents.

---

## 3. Transparency & Explainability

### 3.1 Agent-Level Explainability

Every `AgentResponse` carries four explainability artefacts:

| Field | Purpose |
|-------|---------|
| `reasoning` | Human-readable explanation of what the agent assessed |
| `decision_trace` | Ordered list of agent decisions (breadcrumb audit trail) |
| `sharp_metadata` | Structured governance data (confidence, hallucination risk, audit flags) |
| `low_confidence_fields` | JSON paths to resume fields with uncertain extractions (ExtractorAgent) |

### 3.2 Updated Output Schemas Aid Explainability

The new JSON-path-based schemas increase explainability by anchoring every finding to a specific part of the resume:

- `ResumeCriticReport.issues[].location` -- exact JSON path (e.g., `work[0].highlights[1]`)
- `ContentStrengthReport.suggestions[].location` -- exact JSON path for each suggestion
- `AlignmentReport.skillsMatch[]` / `experienceMatch[]` -- JSON paths into the resume

This allows the UI to highlight the exact resume element being critiqued, rather than displaying general comments.

### 3.3 System-Level Explainability (Langfuse)

Every orchestration run creates a Langfuse trace rooted at `orchestration_execution`, with nested spans per agent. LLM-as-a-judge scores are attached to the same trace via `langfuse.score()`:

```
orchestration_execution (session_id=abc)
  +-- run_agent: ResumeCriticAgent
  |     +-- resume_critic_process (@observe)
  |           +-- call_gemini span
  |
  +-- llm_judge: quality=0.85, accuracy=0.88, helpfulness=0.80
```

### 3.4 Pipeline-Stage XAI Mapping

| Stage | XAI Control |
|-------|-------------|
| Input normalisation | Schema validation logs; ExtractorAgent `_confidence` block |
| LLM call | Langfuse span records truncated prompt and response |
| Output parsing | `parse_and_validate()` raises structured `ValidationError` on schema mismatch |
| Governance audit | `sharp_metadata` added to every response |
| HITL gate | UI presents agent reasoning, location-annotated issues, and suggestions before user approves |
| LLM Judge evaluation | Independent quality/accuracy/helpfulness scores attached to Langfuse trace |

---

## 4. Human Oversight & Control (HITL)

### 4.1 Human-in-the-Loop Design

The system is designed so that **no agent output automatically modifies a resume or triggers an action**. All substantive outputs are surfaced to the user for approval.

| Workflow Step | HITL Gate |
|---------------|-----------|
| Resume extraction | `needs_review=True` returns `NormalizationFailure`; user must review before analysis proceeds |
| Resume structure critique | User reviews location-annotated issues before applying |
| Content strength analysis | User reviews faithful suggestions before editing resume |
| Job alignment | User reviews `missingSkills` and `experienceMatch` paths before tailoring resume |
| Interview coaching | User provides responses; evaluator gate controls progression |
| Voice interview | User controls session start/stop; no autonomous resume modification |
| Low-confidence responses | `confidence_check_passed=false` in `sharp_metadata` signals UI to prompt user caution |
| Bias-flagged interview content | `requires_human_review` in `audit_flags` signals UI to display warning |

### 4.2 HITL State Management

`SessionContext` tracks conversation state. When `sharp_metadata["governance_audit"] == "flagged"`, the frontend surfaces a warning indicator; `audit_flags` provides the specific reason.

### 4.3 Override Capability

Users can reject any suggestion from any agent. The system never applies changes autonomously.

---

## 5. Privacy & Data Minimisation

### 5.1 PII Handling

| Control | Implementation |
|---------|---------------|
| **LLM Guard Anonymize scanner** | Optionally strips PII from prompts before sending to Gemini when `HAS_SPACY=True` |
| **LLM Guard Sensitive scanner** | Flags PII in agent responses |
| **OutputSanitizer** | Defence-in-depth PII stripping on all agent outputs |
| **InterviewCoachAgent `SENSITIVE_PATTERNS`** | Regex patterns detect email, phone, SSN in interview messages; sets `sensitive_input_detected` flag |
| **No persistent storage of raw resumes** | Resumes are held in in-memory `SessionStore`; no database persistence |
| **Request size limit** | 20 MB maximum request body |

### 5.2 Data Retention

- Session data is stored in an in-memory `SessionStore`. Sessions are not persisted to disk.
- Langfuse traces contain truncated prompt/response previews (first 1 000 characters), not complete resume text.

### 5.3 Data in Transit

- All HTTP communication uses HTTPS (Cloud Run enforced).
- WebSocket connections use WSS.
- Gemini API calls use HTTPS with Google-managed TLS.

### 5.4 Limitations & Risks

- Full resume text is sent to the Gemini API (a third-party service). Users should be informed via a privacy notice.
- The in-memory session store does not survive a backend restart (acceptable for stateless Cloud Run, but sessions are lost on pod recycling).
- SpaCy-dependent Anonymize/Sensitive scanners are currently disabled (`HAS_SPACY=False`) for RAM constraints -- residual PII risk.

---

## 6. Robustness & Safety

### 6.1 Input Validation

| Layer | Control |
|-------|---------|
| HTTP | Pydantic v2 schema validation rejects malformed requests with HTTP 422 |
| Rate limiter | `slowapi` (20 req/min per IP) prevents API abuse and model DoS |
| LLM Guard | `PromptInjection` scanner blocks known injection patterns |
| InterviewCoachAgent | `PROMPT_INJECTION_PATTERNS` regex detection on message history |
| Anti-jailbreak directive | Appended to every system prompt |
| Untrusted-input declaration | All agents treating resume/JD as data-only |

### 6.2 Output Validation

| Layer | Control |
|-------|---------|
| Schema enforcement | `parse_and_validate()` validates every LLM response against a Pydantic model |
| Hallucination scoring | `SharpGovernanceService.calculate_hallucination_risk()` scores word-level novelty |
| Faithful flag | `ContentStrengthAgent` omits suggestions it cannot make faithfully |
| LLM Guard output scan | `NoRefusal` + `Sensitive` scanners |
| OutputSanitizer | Final sanitisation pass before response leaves the backend |

### 6.3 Fallback Behaviour

- All agent `process()` methods wrap LLM calls in `try/except`. On failure, the exception is logged with full context.
- `NormalizationFailure` is returned to the user when extraction confidence is too low.
- Mock mode (`MOCK_*_AGENT=true`) provides deterministic fallback for testing and development.

---

## 7. Accountability

### 7.1 Audit Trail

Every agent decision is traceable through:
1. **Langfuse trace** (session-level, searchable by `session_id`).
2. **`decision_trace`** field in `AgentResponse` (returned to frontend).
3. **`sharp_metadata`** (governance audit result, timestamps, flags).
4. **Structured JSON logs** emitted to Cloud Run stdout -> Cloud Logging.

### 7.2 Governance Audit Metadata

`SharpGovernanceService.audit()` attaches (example):

```json
{
  "governance_audit": "passed | flagged",
  "audit_timestamp": 1711234567890,
  "hallucination_check_passed": true,
  "confidence_check_passed": true,
  "audit_flags": ["low_confidence", "hallucination_risk", "bias_review_required",
                  "sensitive_interview_content", "requires_human_review"],
  "unfaithful_suggestions": 0
}
```

### 7.3 LLM-as-a-Judge Accountability

`LLmasJudgeEvaluator` provides an independent second-opinion on every agent output in evaluation runs. Quality/accuracy/helpfulness scores are attached to Langfuse traces, enabling:
- Regression detection between code versions.
- Per-agent performance trending over time.
- Identification of systematic weaknesses.

### 7.4 Version Tracking

- `APP_ENV` and `settings.VERSION` are logged with every trace.
- Docker images are tagged with `github.sha`, providing immutable build provenance.

---

## 8. Governance Framework (SHARP)

The **SHARP Governance Service** (`app/governance/sharp_governance_service.py`) implements the following checks on every agent response:

| Check | Threshold | Action on Failure |
|-------|-----------|------------------|
| Confidence threshold | >= 0.3 | Flag `low_confidence` |
| Hallucination risk | < 0.7 | Flag `hallucination_risk` |
| Unfaithful suggestions | 0 | Flag `unfaithful_suggestions`, `requires_human_review` |
| Bias patterns detected (InterviewCoach) | 0 | Flag `bias_review_required`, `requires_human_review` |
| Sensitive content detected (InterviewCoach) | 0 | Flag `sensitive_interview_content`, `requires_human_review` |
| Prompt injection detected (InterviewCoach) | 0 | Flag `prompt_injection_attempt`, `requires_human_review` |

### 8.1 SHARP Principle Alignment

| SHARP Pillar | Implementation |
|--------------|---------------|
| **S**afety | Prompt-injection blocking (LLM Guard + regex), output sanitisation, rate limiting, request size limits |
| **H**onesty | Faithful flag on suggestions, hallucination risk score, JSON-path location references |
| **A**ccountability | Audit trail via Langfuse, decision_trace, governance metadata, LLM-as-judge scores |
| **R**esponsibility | HITL gates, low-confidence flagging, bias/sensitive/injection detection in InterviewCoachAgent |
| **P**rivacy | LLM Guard anonymisation, OutputSanitizer, SENSITIVE_PATTERNS in InterviewCoachAgent, HTTPS everywhere |

---

## 9. Responsible AI Lifecycle Alignment

| Lifecycle Stage | Controls Applied |
|-----------------|-----------------|
| **Design** | Agent scope limited to advisory; no autonomous changes; HITL by design; bias patterns codified |
| **Development** | Mock mode for safe testing; Pydantic v2 schema contracts; unit + integration + structural tests |
| **Deployment** | Trivy security scanning in CI/CD; environment tagging; staged rollout; rate limiting |
| **Operation** | Langfuse real-time monitoring; LLM judge scores; confidence trend alerts; prompt version tracking |
| **Evaluation** | `evals/` dataset package; `eval-runner.yml` CI workflow; `test_agent_evals.py` and `test_agent_structural_checks.py` |
| **Decommission** | Stateless containers; no persistent model weights; session data in-memory only |

---

## 10. Gaps & Improvement Roadmap

| Gap | Recommended Action | Priority |
|-----|--------------------|----------|
| No demographic bias testing | Implement diverse resume benchmark | High |
| SpaCy PII scanner disabled for RAM | Re-enable with dedicated sidecar | Medium |
| User-facing privacy notice absent | Add privacy notice to frontend onboarding | High |
| Voice interview (GeminiLive) not covered by SHARP audit | Add governance wrapper for WebSocket session metadata | Medium |
| LLM-as-judge not run in production | Enable sampled live eval (`EVAL_SAMPLE_RATE=0.1`) | Medium |
| No formal model card | Publish model card for Gemini usage in this context | Low |
