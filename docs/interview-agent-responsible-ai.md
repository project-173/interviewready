# Interview Agent Security and Responsible AI

This implementation is aligned to the IMDA/PDPC Model AI Governance Framework pillars of internal governance, human involvement, operations management, and stakeholder communication, and to Singapore guidance that AI should be explainable, transparent, fair, and human-centric.

## Agent-specific security risks

- Prompt injection through candidate answers, resume content, or job descriptions.
- PII exposure in resumes, message history, or interview summaries.
- Biased or discriminatory coaching if the job description contains protected-attribute signals.
- Over-retention of sensitive interview content in downstream summaries and traces.

## Mitigations implemented

- Code level:
  - `BaseAgent` scans inputs for prompt-injection patterns and sanitizes outputs.
  - `InterviewCoachAgent` screens candidate-controlled text for adversarial or prompt-injection patterns before model execution and blocks suspicious replies with a deterministic re-ask.
  - `InterviewCoachAgent` redacts direct identifiers such as email, phone, and SSN before prompt construction.
  - `InterviewCoachAgent` keeps redacted interview answers for completion-summary generation.
  - `InterviewCoachAgent` emits structured explainability, bias, and governance metadata in `sharp_metadata`.
- Workflow level:
  - `SharpGovernanceService` audits interview responses and flags human review when sensitive-content or bias signals appear.
  - Governance also flags blocked prompt-injection attempts for audit and follow-up.
  - The deploy workflow runs targeted interview security and governance tests before image build and deployment.
  - Existing Trivy scans remain in the deployment workflow for repository and container-image risk visibility.

## Explainable and Responsible AI alignment

### Development

- The interview flow uses schema-constrained JSON to keep outputs predictable and inspectable.
- Decision traces and reasoning fields record why the agent scored or advanced a response.
- Deterministic fallback scoring reduces silent failure when the model omits progression metadata.
- Adversarial-input tests cover prompt-injection attempts, suspicious markup, sensitive-content redaction, and governance escalation.

### Deployment

- Every agent response is passed through governance auditing after orchestration.
- CI now enforces interview-agent and governance tests before deployment proceeds.
- Langfuse-compatible tracing supports auditability and post-deployment monitoring.
- The deployment path preserves safety evidence because governance metadata is merged rather than overwritten.

## How the interview agent addresses explainability

- The response includes `feedback`, `answer_score`, `can_proceed`, and `next_challenge` so users can understand progression decisions.
- `decision_trace` records the question number, model path, and scoring basis.
- `reasoning` summarizes that coaching decisions are based on resume-job alignment and answer-quality heuristics.
- Structured metadata also maps controls to IMDA governance domains so review teams can trace how development and deployment practices meet governance expectations.

## Bias mitigation

- The agent is instructed not to infer protected attributes or personalize coaching on that basis.
- Potentially biased language in job descriptions is detected and surfaced through metadata for governance review.
- Coaching remains anchored to evidence in the resume, the job description, and the candidate answer.
- The interview agent is advisory only; it does not make autonomous hiring decisions, which reduces fairness and accountability risk.

## Sensitive content and governance alignment

- Direct identifiers are redacted before prompts reach the model.
- Redacted answers are used for interview completion summaries.
- Sensitive-content and bias signals populate `sharp_metadata`, and governance can flag `requires_human_review`.
- Prompt-injection attempts are treated as security events and surfaced through governance metadata.

## IMDA Model AI Governance Framework alignment

### Internal governance structures and measures

- Agent-specific risks, mitigations, and Responsible AI metadata are attached to every interview response.
- CI now enforces targeted interview-agent security and governance tests before deployment.

### Human involvement in AI-augmented decision-making

- The interview agent provides coaching support only and does not take autonomous employment actions.
- Sensitive, biased, or adversarial cases trigger `human_review_recommended` and governance flags.

### Operations management

- Untrusted user text is screened for prompt injection before model calls.
- Inputs are redacted for direct identifiers before prompts are built.
- Post-response governance audits preserve and evaluate interview safety metadata.

### Stakeholder interaction and communication

- Users receive explainable fields such as `feedback`, `answer_score`, `can_proceed`, and `next_challenge`.
- Reviewers receive decision traces and structured governance metadata for auditability.
