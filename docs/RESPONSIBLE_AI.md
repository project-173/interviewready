# Explainable and Responsible AI Report — InterviewReady

## 1. Introduction

This report documents how Explainable AI (XAI) and Responsible AI (RAI) principles have been considered, embedded, and operationalised throughout the InterviewReady system. It maps each stage of the agent pipeline to specific principles and controls, and identifies areas for continuous improvement.

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
| **Representational bias** | LLM trained on Western career corpora may penalise non-Western resume formats (reverse-chronological not universal) | ResumeCriticAgent |
| **Keyword bias** | JobAlignmentAgent may over-fit to JD keywords and under-weight equivalent skills phrased differently | JobAlignmentAgent |
| **Confidence inflation** | ContentStrengthAgent may assign higher evidence strength to candidates with quantified achievements, disadvantaging entry-level candidates | ContentStrengthAgent |
| **Interview question bias** | InterviewCoachAgent may generate questions culturally specific to certain regions | InterviewCoachAgent |

### 2.2 Mitigations Implemented

**Faithfulness constraint** (`ContentStrengthAgent` system prompt):
```
NEVER invent new skills, achievements, or experiences.
If suggestion requires fabrication, mark faithful=false.
```
This prevents the LLM from "improving" a resume in a way that advantages candidates from backgrounds well-represented in training data.

**`SharpGovernanceService` — unfaithful suggestion flagging:**
Suggestions marked `faithful=false` are surfaced to the user before any action is taken, placing the bias decision in human hands.

**Confidence threshold enforcement:**
Responses with `confidence_score < 0.3` are flagged as `low_confidence`, preventing low-quality (potentially biased) outputs from reaching users silently.

**Prompt versioning via Langfuse:**
All system prompts are tracked. Drift in prompt content that might introduce new bias is detectable by comparing prompt versions in the Langfuse dashboard.

### 2.3 Future Recommendations

- Implement a diverse test-resume benchmark spanning multiple nationalities, education levels, and experience domains to detect differential treatment.
- Add a bias audit step using LLM-as-a-judge with an explicit diversity rubric.
- Introduce configurable cultural context (e.g., resume region) as an input parameter.

---

## 3. Transparency & Explainability

### 3.1 Agent-Level Explainability

Every `AgentResponse` carries three explainability artefacts:

| Field | Purpose |
|-------|---------|
| `reasoning` | Human-readable explanation of what the agent assessed |
| `decision_trace` | Ordered list of agent decisions (e.g., "Analysed 4 skills", "Hallucination risk: 0.12") |
| `sharp_metadata` | Structured governance data (confidence, hallucination risk, audit flags) |

Example `decision_trace` from `ContentStrengthAgent`:
```
[
  "ContentStrengthAgent: Analysed resume for skills and achievements",
  "ContentStrengthAgent: Identified 5 skills",
  "ContentStrengthAgent: Identified 3 achievements",
  "ContentStrengthAgent: Generated 4 suggestions",
  "ContentStrengthAgent: Hallucination risk: 0.12"
]
```

### 3.2 System-Level Explainability (Langfuse)

Every orchestration run creates a Langfuse trace rooted at `orchestration_execution`, with nested spans:

```
orchestration_execution (session_id=abc)
  └── run_agent: ResumeCriticAgent
        └── resume_critic_process (Langfuse @observe)
              └── call_gemini span
                    ├── input: { prompt_preview }
                    └── output: { response_preview }
```

Traces are filterable by `session_id`, `agent`, `environment`, and `confidence`. This enables:
- Post-hoc explanation of any specific recommendation.
- Audit trail available to system administrators.

### 3.3 Pipeline-Stage Mapping

| Stage | XAI Control |
|-------|-------------|
| Input normalisation | Schema validation logs with Pydantic validation errors |
| LLM call | Langfuse span records truncated prompt and response |
| Output parsing | `parse_and_validate()` raises structured `ValidationError` on schema mismatch |
| Governance audit | `sharp_metadata` added to every response |
| HITL gate | UI presents agent reasoning and suggestions before user approves |

---

## 4. Human Oversight & Control (HITL)

### 4.1 Human-in-the-Loop Design

The system is designed around the principle that **no agent output automatically modifies a resume or triggers an action**. All substantive outputs are surfaced to the user for approval.

| Workflow Step | HITL Gate |
|---------------|-----------|
| Resume structure critique | User reviews `formattingRecommendations` and `suggestions` before applying |
| Content strength analysis | User reviews `suggestions` (faithful/unfaithful) before editing resume |
| Job alignment | User reviews `missingKeywords` and `recommendations` before tailoring resume |
| Interview coaching | User provides responses; agent evaluates each turn; user chooses to continue |
| Low-confidence responses | `confidence_check_passed=false` in `sharp_metadata` signals UI to prompt user caution |

### 4.2 HITL State Management

`SessionContext` tracks the conversation state. When `sharp_metadata["governance_audit"] == "flagged"`, the frontend is expected to surface a warning indicator, and the `decision_trace` provides the reason.

### 4.3 Override Capability

Users can reject any suggestion from any agent. Rejected suggestions are not applied. The system never applies changes autonomously.

---

## 5. Privacy & Data Minimisation

### 5.1 PII Handling

| Control | Implementation |
|---------|---------------|
| **LLM Guard Anonymize scanner** | Optionally strips PII (names, emails, phone numbers) from prompts before sending to Gemini when `HAS_SPACY=True` |
| **Output sensitive scanner** | LLM Guard `Sensitive` scanner flags PII in agent responses |
| **OutputSanitizer** | Defence-in-depth PII stripping on all agent outputs (`app/utils/output_sanitizer.py`) |
| **No persistent storage of raw resumes** | Resumes are held in `SessionContext` (in-memory session store); no database persistence of raw resume text |
| **Request size limit** | 20 MB maximum request body prevents bulk data exfiltration attempts |

### 5.2 Data Retention

- Session data is stored in an in-memory `SessionStore` (`app/api/v1/session_store.py`). Sessions are not persisted to disk in the current release.
- Langfuse traces contain truncated prompt/response previews (first 1000 characters), not complete resume text.

### 5.3 Data in Transit

- All communication between frontend and backend uses HTTPS (Cloud Run enforced).
- Gemini API calls use HTTPS with Google-managed TLS.

### 5.4 Limitations & Risks

- Full resume text is sent to the Gemini API (a third-party service). Users should be informed via a privacy notice.
- Langfuse traces store metadata and truncated content. Keys must be rotated if compromised.
- The in-memory session store does not survive a backend restart; this is acceptable for the current stateless Cloud Run deployment but means sessions are lost on pod recycling.

---

## 6. Robustness & Safety

### 6.1 Input Validation

| Layer | Control |
|-------|---------|
| HTTP | Pydantic v2 schema validation rejects malformed requests with HTTP 422 |
| LLM Guard | `PromptInjection` scanner blocks known injection patterns |
| Anti-jailbreak directive | Appended to every system prompt to resist role-play and schema override attacks |

### 6.2 Output Validation

| Layer | Control |
|-------|---------|
| Schema enforcement | `parse_and_validate()` validates every LLM response against a Pydantic model |
| Hallucination scoring | `SharpGovernanceService.calculate_hallucination_risk()` scores word-level novelty |
| Quantifiable claim detection | `contains_quantifiable_claim()` verifies numeric claims are grounded |
| Faithful flag | `ContentStrengthAgent` marks each suggestion's factual groundedness |
| LLM Guard output scan | `NoRefusal` scanner detects unhelpful refusals; `Sensitive` detects leaked PII |
| OutputSanitizer | Final sanitisation pass before response leaves the backend |

### 6.3 Fallback Behaviour

- All agent `process()` methods wrap the LLM call in `try/except`. On failure, the exception is logged with full context and re-raised to the orchestrator, which returns a structured error `AgentResponse`.
- Mock mode (`MOCK_*_AGENT=true`) provides deterministic fallback for testing and development.

---

## 7. Accountability

### 7.1 Audit Trail

Every agent decision is traceable through:
1. **Langfuse trace** (session-level, searchable by `session_id`).
2. **`decision_trace`** field in `AgentResponse` (returned to frontend).
3. **`sharp_metadata`** (governance audit result, timestamps, flags).
4. **Structured JSON logs** (`app/core/logging.py`) emitted to Cloud Run's stdout → Cloud Logging.

### 7.2 Governance Audit Metadata

`SharpGovernanceService.audit()` attaches:

```json
{
  "governance_audit": "passed | flagged",
  "audit_timestamp": 1711234567890,
  "hallucination_check_passed": true,
  "confidence_check_passed": true,
  "audit_flags": ["low_confidence", "hallucination_risk"],
  "unfaithful_suggestions": 1,
  "high_evidence_skills_count": 3
}
```

### 7.3 Version Tracking

- `APP_ENV` and `settings.VERSION` are logged with every trace, enabling per-version accountability.
- Docker images are tagged with `github.sha`, providing an immutable build provenance link.

---

## 8. Governance Framework (SHARP)

The **SHARP Governance Service** (`app/governance/sharp_governance_service.py`) implements the following checks on every agent response:

| Check | Threshold | Action on Failure |
|-------|-----------|------------------|
| Confidence threshold | ≥ 0.3 | Flag `low_confidence` |
| Hallucination risk | < 0.7 | Flag `hallucination_risk` |
| Unfaithful suggestions | 0 | Flag `unfaithful_suggestions`, `requires_human_review` |
| New proper nouns in output | Heuristic | Contributes to hallucination risk score |
| New numbers in output | Heuristic | Contributes to hallucination risk score |

### 8.1 SHARP Principle Alignment

| SHARP Pillar | Implementation |
|--------------|---------------|
| **S**afety | Prompt-injection blocking, output sanitisation, request size limits |
| **H**onesty | Faithful flag on suggestions, hallucination risk score |
| **A**ccountability | Audit trail via Langfuse, decision_trace, governance metadata |
| **R**esponsibility | HITL gates, low-confidence flagging, bias controls |
| **P**rivacy | LLM Guard anonymisation, OutputSanitizer, HTTPS everywhere |

---

## 9. Responsible AI Lifecycle Alignment

| Lifecycle Stage | Controls Applied |
|-----------------|-----------------|
| **Design** | Agent scope limited to advisory; no autonomous changes; HITL by design |
| **Development** | Mock mode for safe testing; Pydantic v2 schema contracts; unit + integration tests |
| **Deployment** | Trivy security scanning in CI/CD; environment tagging; staged rollout |
| **Operation** | Langfuse real-time monitoring; confidence trend alerts; prompt version tracking |
| **Decommission** | Stateless containers; no persistent model weights; session data in-memory only |

---

## 10. Gaps & Improvement Roadmap

| Gap | Recommended Action | Priority |
|-----|--------------------|----------|
| No demographic bias testing | Implement diverse resume benchmark | High |
| Manual HITL only | Add automated quality gate (LLM-as-a-judge) | Medium |
| Langfuse trace contains truncated content | Full content optional behind admin flag | Low |
| SpaCy PII scanner disabled for RAM | Re-enable with dedicated spaCy sidecar | Medium |
| No formal model card | Publish model card for Gemini usage in this context | Medium |
| No user-facing privacy notice | Add privacy notice to frontend onboarding | High |
