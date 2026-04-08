# InterviewReady: AI-Powered Resume & Interview Optimization Platform

An intelligent multi-agent AI system for comprehensive resume optimization and interview preparation, aligned with IMDA explainable and responsible AI governance principles.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Strategic Context & Design Rationale](#strategic-context--design-rationale)
3. [System Architecture](#system-architecture)
4. [Agent System Design](#agent-system-design)
5. [Explainable & Responsible AI Practices](#explainable--responsible-ai-practices)
6. [AI Security Risk Register](#ai-security-risk-register)
7. [MLSecOps/LLMSecOps Pipeline](#mlsecopsllmsecops-pipeline)
8. [Testing Summary](#testing-summary)
9. [Quick Start Guide](#quick-start-guide)
10. [Deployment & Operations](#deployment--operations)

---

## 1. Introduction

### 1.1 Project Objective & Scope

**Objective:** InterviewReady empowers job candidates to present their qualifications effectively through AI-powered analysis while ensuring fair, transparent, and governance-aligned guidance enabled by a multi-agent orchestration system that evaluates resume quality, analyzes job alignment, and provides realistic interview coaching.

**Scope:**
- **In Scope:** Resume parsing & structural analysis, content strength evaluation, job description semantic alignment, role-specific interview coaching with answer evaluation, multi-turn interview simulation, comprehensive governance auditing, session-based state management, real-time feedback with explainability.
- **Out of Scope:** Autonomous hiring decisions, resume storage/persistence beyond sessions, third-party ATS integration, employment recommendation authority.

### 1.2 Solution Overview

InterviewReady implements a **Multi-Agent Orchestration** architecture with specialized agents collaborating to provide holistic resume and interview optimization:

**Core Design Principles:**
- **Separation of Concerns:** Each agent has a single, well-defined purpose
- **Governance-First:** Security, bias, and fairness checks at every step
- **Explainability:** Every decision includes reasoning, decision_trace, and confidence metrics
- **Observability:** Complete traceability via Langfuse and structured JSON logging
- **Resilience:** Graceful fallbacks for model failures and service errors

### 1.3 High-Level Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User Request                             │
│  (Resume Data/File + Intent + Job Description)             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────┐
        │   Resume Extraction      │
        │   (ExtractorAgent)       │
        │  - PDF parsing           │
        │  - Structured data       │
        │  - Confidence scoring    │
        └────────────┬─────────────┘
                     │
                     ▼
        ┌──────────────────────────┐
        │  Intent Classification   │
        │  (Orchestration Layer)   │
        └────────────┬─────────────┘
                     │
        ┌────────────┴────────────┬────────────┬────────────┐
        │                         │            │            │
   RESUME_CRITIC         CONTENT_STRENGTH   ALIGNMENT    INTERVIEW_COACH
        │                         │            │            │
        ▼                         ▼            ▼            ▼
    ┌────────────┐        ┌──────────────┐┌────────────┐┌──────────────┐
    │ResumeCritic│        │ContentStrength││JobAlignment││InterviewCoach│
    │Agent       │        │Agent          ││Agent       ││Agent         │
    └────────────┘        └──────────────┘└────────────┘└──────────────┘
        │                         │            │            │
        └────────────┬────────────┴────────────┴────────────┘
                     │
                     ▼
        ┌──────────────────────────────┐
        │  SHARP Governance Audit      │
        │  - Bias Detection            │
        │  - Hallucination Assessment  │
        │  - Confidence Validation     │
        │  - Security Checks           │
        └────────────┬─────────────────┘
                     │
                     ▼
        ┌──────────────────────────────┐
        │     Unified Response         │
        │  + Decision Trace            │
        │  + Governance Metadata       │
        │  + Confidence Score          │
        └──────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────┐
        │     Langfuse Tracing &       │
        │     LLM Guard Security       │
        └──────────────────────────────┘
                     │
                     ▼
                User Response
```

---

## 2. Strategic Context & Design Rationale

This section answers the key architectural, stakeholder, governance, and lifecycle questions that justify the multi-agent approach taken by InterviewReady.

### 2.1 Key Pain Points Addressed by Multi-Agent AI

**Current workflow gaps in job preparation:**

| Pain Point | How InterviewReady Addresses It |
|------------|--------------------------------|
| Resume quality varies widely; candidates cannot self-audit ATS compatibility | `ResumeCriticAgent` provides objective, rubric-based structural analysis with scoring |
| Content lacks quantifiable evidence; weak achievement framing | `ContentStrengthAgent` identifies evidence gaps and suggests specific improvements |
| Misalignment between resume content and job description is invisible until rejection | `JobAlignmentAgent` performs semantic gap analysis with prioritized missing-skill recommendations |
| Interview preparation is isolated from resume context | `InterviewCoachAgent` generates role-specific questions rooted in resume evidence and JD requirements |
| No feedback loop between analysis stages | Shared session state preserves findings across all agents, enabling cumulative insight |
| Human bias in resume screening is pervasive | Governance layer enforces protected-attribute non-inference and bias-flag propagation |

**Additional value beyond gap-filling (proactive intelligence):**

Even without explicit user requests, the system proactively:
- **Detects hallucination risk** in resume content before it reaches the interviewer (confidence threshold gate)
- **Surfaces hidden skill gaps** by cross-referencing job description semantics against resume evidence, not just keyword matching
- **Flags interview-ready risk** when answer quality drops below rubric thresholds (LLM-as-a-judge scoring)
- **Identifies PII exposure** in user inputs and redacts it before any LLM call, protecting candidates from inadvertent data leakage
- **Escalates edge cases** (low-confidence extraction, ambiguous job requirements, sensitive content) to human review automatically

### 2.2 Pros and Cons of Agentic AI Adoption

**Pros:**

| Dimension | Benefit |
|-----------|---------|
| **Specialisation** | Each agent is an expert in its task—prompts, output schemas, and validation logic are optimised for a single concern |
| **Modularity** | Agents can be updated, replaced, or extended independently without touching other components |
| **Explainability** | Every decision includes `decision_trace`, `reasoning`, and `confidence_score`—monolithic LLMs cannot offer this granularity |
| **Governance** | SHARP Governance Service applies consistent audit rules to all agents from a single, auditable location |
| **Scalability** | Agents are stateless (except InterviewCoach) and can scale horizontally on Cloud Run independently |
| **Resilience** | Mock fallback per-agent means a single API failure does not bring down the entire system |
| **Testing** | Each agent can be unit-tested in isolation; security tests target specific agent vulnerabilities |
| **Proactive intelligence** | Agents can detect hidden risks (hallucination, bias, PII) that a simple chatbot would silently propagate |

**Cons / Trade-offs:**

| Dimension | Challenge & Mitigation |
|-----------|------------------------|
| **Latency** | Multi-agent orchestration adds overhead. Mitigated via LangGraph parallel dispatch and mock fallback for non-critical paths |
| **Complexity** | More moving parts than a single chatbot. Mitigated by strict interface contracts (`BaseAgent`, `AgentResponse`) and comprehensive test coverage |
| **LLM costs** | Multiple Gemini calls per request. Mitigated by per-agent mock mode (dev/CI) and cost tracking via Langfuse |
| **Coordination failures** | State inconsistency if one agent fails mid-flow. Mitigated by LangGraph checkpoint recovery and session state isolation |
| **Governance overhead** | SHARP audit adds processing time per response. Mitigated by non-blocking, in-process governance checks |
| **Prompt maintenance** | More prompts to maintain across agents. Mitigated by BaseAgent mixin, shared directives, and version-tracked system prompts |

### 2.3 Key Stakeholders

| Stakeholder | Role | Primary Concern |
|-------------|------|-----------------|
| **Job Seekers (primary users)** | Interact with all agents to optimise resume and prepare for interviews | Quality, privacy, fairness of feedback |
| **HR / Hiring Managers** | Indirect beneficiaries; receive better-prepared candidates | Candidate quality; no adverse selection |
| **Platform Developers / MLEs** | Build and maintain agents, orchestration, governance | Code quality, test coverage, security |
| **AI Governance / Ethics Reviewers** | Review SHARP audit trails, bias flags, escalation rates | Fairness, explainability, IMDA compliance |
| **Security Team** | Review LLM Guard outputs, Langfuse traces, CI security scans | Prompt injection, PII leakage, hallucination |
| **Product / Project Owner** | Scope, roadmap, stakeholder reporting | Feature completeness, demo readiness |
| **Cloud / DevOps** | Manage GCP Cloud Run, CI/CD pipeline, secret management | Reliability, cost, deployment velocity |
| **Regulators / Compliance** | PDPA (Singapore), IMDA AI Governance Framework alignment | Data handling, fairness, accountability trail |

### 2.4 Agent Coordination for Seamless User Experience

Agents coordinate through a **shared session state** managed by the LangGraph Orchestration Engine:

```
User request (intent + resume + JD)
  │
  ▼
OrchestrationAgent (LangGraph state machine)
  ├─ Reads: session_id → retrieves prior context
  ├─ Routes: intent → target agent(s)
  ├─ Passes: resume_data (normalised by ExtractorAgent if PDF)
  ├─ Passes: job_description (shared across all agents)
  ├─ Passes: message_history (for InterviewCoach multi-turn state)
  │
  ├─ ResumeCriticAgent (stateless)     ← returns critique + decision_trace
  ├─ ContentStrengthAgent (stateless)  ← returns skills analysis + confidence
  ├─ JobAlignmentAgent (stateless)     ← returns alignment score + gaps
  └─ InterviewCoachAgent (stateful)    ← reads/writes question history, scores
        │
        ▼
  SHARP Governance Audit (all agents)
        │
        ▼
  Response aggregated with decision_trace + governance metadata
        │
        ▼
  Session state updated (Langfuse span committed)
        │
        ▼
  Client renders unified response
```

**Coordination mechanisms:**
- **Shared resume context:** All agents receive normalised `Resume` Pydantic model; ExtractorAgent enriches it if PDF is provided
- **Session persistence:** `SessionContext` carries prior analysis results so InterviewCoach can reference ResumeCritic findings without redundant LLM calls
- **Governance as shared service:** A single `SharpGovernanceService` instance audits every agent response uniformly
- **Decision trace aggregation:** Each agent appends to the same `decision_trace` array, giving users a complete reasoning chain
- **Error isolation:** LangGraph routes around failed agents; mock fallback prevents cascading failures

### 2.5 Modular Agentic vs. Monolithic Chatbot

| Attribute | Monolithic Chatbot | InterviewReady Multi-Agent |
|-----------|--------------------|---------------------------|
| **Workload reduction** | Single prompt must cover all tasks | Each agent has a focused, optimised prompt with purpose-built validation |
| **User guidance quality** | Generic advice | Resume-evidence-anchored, JD-specific, rubric-scored guidance |
| **Flexibility** | Changing behaviour requires modifying the monolith | Add/replace one agent without touching others |
| **Explainability** | Black box—no traceable decision path | `decision_trace` + `reasoning` + `confidence_score` per response |
| **Traceability** | Difficult to audit individual decisions | Langfuse distributed traces; per-agent governance metadata |
| **Failure isolation** | One bad prompt degrades whole system | Agent failures caught; mock fallback maintains service |
| **Security surface** | Entire system is one target | Per-agent LLM Guard + governance; attack surfaces isolated |
| **Testing** | Integration tests only | Unit tests per agent + governance + security + structural + eval tests |

### 2.6 Demo Scenarios Showing Agentic Value

| Scenario | What to Demonstrate | Expected Observable Behaviour |
|----------|--------------------|-----------------------------|
| **Resume critique flow** | ResumeCriticAgent on a weak ATS resume | Score < 70, structured issues list, `decision_trace` shows section-by-section evaluation |
| **Content strength uplift** | Before/after ContentStrength on a resume with no metrics | `hallucinationRisk` drops when user adds quantified achievements |
| **Job alignment gap detection** | JobAlignmentAgent on a misaligned resume | `missingSkills` with criticality ranking; `fitScore` below 50% |
| **Multi-turn interview coach** | 5-question session with weak answer on Q2 | `can_proceed: false` → coach re-asks; `score` increases on Q2 retry |
| **Bias flag escalation** | Job description with age-biased language | `bias_review_required: true` in governance metadata; `requires_human_review` flag visible |
| **Prompt injection defence** | User embeds "ignore previous instructions" in resume text | LLM Guard blocks input; `decision_trace` records security event; no LLM call made |
| **PDF extraction confidence gate** | Ambiguous PDF with missing fields | `needs_review: true`, `low_confidence_fields` list shown to user |
| **Langfuse trace audit** | Show Langfuse dashboard after a session | Full span tree: orchestration → agent → governance → response, with cost and latency |

### 2.7 Scale & Scalability

**Design target:** 50–200 concurrent user sessions with < 5 second p95 latency per agent response.

**Scalability characteristics:**

| Dimension | Mechanism | Justification |
|-----------|-----------|---------------|
| **Horizontal scaling** | Google Cloud Run auto-scales replicas based on concurrency | Each backend container handles ~10–20 concurrent requests; Cloud Run spins up new instances within seconds |
| **Stateless agents** | ResumeCritic, ContentStrength, JobAlignment are fully stateless | Can scale to any number of replicas without shared memory |
| **Rate limiting** | `slowapi` rate limiter on all API endpoints | Prevents quota exhaustion and ensures fair resource distribution |
| **Async processing** | FastAPI + asyncio; all Gemini calls are async | Maximises I/O throughput per container instance |
| **Mock fallback** | Instant mock responses when Gemini API is unavailable | Maintains UX under API quota limits or outages |

**Demonstrating/justifying scalability:**
- Cloud Run console shows auto-scaling events and replica count under load
- `GET /api/v1/health` endpoint reports `status`, service health, and version
- Langfuse traces show per-agent latency distribution across sessions
- Load tests against `/api/v1/chat` demonstrate concurrency handling

### 2.8 Explainability & Traceability of Agent Decisions

Every `AgentResponse` includes four explainability artefacts:

| Field | Content | Consumer |
|-------|---------|---------|
| `decision_trace` | Ordered list of reasoning steps | End users, auditors |
| `reasoning` | Agent narrative explanation of approach | End users, governance reviewers |
| `confidence_score` | 0.0–1.0 certainty metric; < 0.3 triggers `requires_human_review` | Governance layer, HITL escalation |
| `sharp_metadata` | Structured governance audit output: `governance_audit`, `audit_flags`, `hallucination_check_passed`, `audit_timestamp` | Security, compliance, AI ethics reviewers |

Additionally:
- **Langfuse distributed tracing** records every LLM call correlated by `session_id`
- **Structured JSON logs** carry `session_id`, `agent_name`, `intent`, and timing
- **LLM-as-a-judge evaluation** scores agent output quality on curated datasets post-deployment

### 2.9 Safeguards for Bias, Fairness, Accountability & Trust

| Safeguard | Implementation | Evidence |
|-----------|---------------|---------|
| **Protected attribute non-inference** | System prompts explicitly forbid agents from inferring age, gender, ethnicity, nationality | `ANTI_JAILBREAK_DIRECTIVE` in InterviewCoachAgent |
| **Bias pattern detection** | `BIAS_PATTERNS` regex set scans job descriptions and agent outputs | `governance/sharp_governance_service.py` |
| **Confidence threshold gate** | Responses with `confidence_score < 0.3` flagged for human review | `SharpGovernanceService._validate_confidence()` |
| **Hallucination risk assessment** | NLI-based consistency check between suggestion and source text | `SharpGovernanceService.hallucination_risk_assessment()` |
| **Prompt injection defence** | LLM Guard scans all user inputs before any LLM call | `BaseAgent._scan_input()` |
| **PII redaction** | `SENSITIVE_PATTERNS` redact SSN, email, phone before prompt construction | `InterviewCoachAgent.SENSITIVE_PATTERNS` |
| **Governance audit trail** | `sharp_metadata` preserved in every response and Langfuse trace | `SharpGovernanceService.audit()` |
| **Human-in-the-loop escalation** | `requires_human_review` flag surfaced to UI when governance fails | `AgentResponse.needs_review` field |
| **Evaluation pipeline** | LLM-as-a-judge scores responses on bias, hallucination, and quality dimensions | `evals/run_evals.py` + Langfuse datasets |

### 2.10 Common Services & Shared Infrastructure

| Shared Service | Technology | Role |
|---------------|-----------|------|
| **Session state** | `SessionContext` (Pydantic) + LangGraph checkpoints | Shared memory across all agents within a session |
| **Structured logging** | Python `logging` with JSON formatter | Centralised log stream; all agents emit to same logger |
| **Distributed tracing** | Langfuse SDK | Session-correlated traces across all agent spans |
| **LLM API gateway** | `GeminiService` singleton | All agents share one configured client; mock mode toggle |
| **Governance service** | `SharpGovernanceService` singleton | Applied to every agent response after orchestration |
| **Input security** | LLM Guard scanner (in-process) | Shared across all agents via `BaseAgent` mixin |
| **Output sanitization** | Output sanitizer (in-process) | Shared across all agents via `BaseAgent` mixin |
| **Rate limiter** | `slowapi` (`app/core/limiter.py`) | Applied at API layer; protects all endpoints |
| **Configuration** | `pydantic_settings.BaseSettings` | Single `.env` / `config.py` for all components |

### 2.11 Reusable Libraries & Frameworks

| Category | Library/Framework | Usage |
|----------|------------------|-------|
| **Agent orchestration** | LangGraph | Stateful multi-agent workflow with checkpointing, conditional routing, error recovery |
| **LLM integration** | LangChain | LLM chain utilities, function calling, prompt templates |
| **LLM input security** | LLM Guard | Prompt injection detection; output scanning |
| **LLM observability** | Langfuse | Distributed tracing, dataset evaluations, cost tracking |
| **Data validation** | Pydantic V2 | Type-safe input/output schemas for all agents and API |
| **Web framework** | FastAPI | Async REST API, OpenAPI docs, dependency injection |
| **Rate limiting** | slowapi | Token bucket rate limiting on all endpoints |
| **Testing** | pytest + pytest-asyncio | Unit, integration, security, governance tests |
| **Frontend** | React 18 + TypeScript | Type-safe SPA with concurrent rendering |
| **Frontend build** | Vite 5 | Fast HMR, optimised production bundles |

### 2.12 AI-Specific Security Risks & Mitigations

| Risk | Category | Severity | Mitigation |
|------|----------|----------|-----------|
| **Prompt injection** | Input attack | HIGH | LLM Guard scanning on all inputs; `PROMPT_INJECTION_PATTERNS` regex; strict schema output |
| **Hallucination** | Output quality | MEDIUM | Confidence threshold gate; NLI-based hallucination risk score; `hallucination_check_passed` flag |
| **PII exposure** | Privacy | HIGH | `SENSITIVE_PATTERNS` redaction before LLM calls; Langfuse trace filtering |
| **Bias injection via JD** | Fairness | MEDIUM | `BIAS_PATTERNS` scan; protected-attribute non-inference directive; governance flag |
| **Jailbreak / adversarial prompts** | Input attack | HIGH | `ANTI_JAILBREAK_DIRECTIVE` in all system prompts; `PROMPT_INJECTION_PATTERNS` in InterviewCoach |
| **API key leakage** | Secrets | CRITICAL | Environment variable injection; GitHub Secrets; no key logging |
| **Supply chain attacks** | Infrastructure | MEDIUM | Trivy container scans; pinned dependency versions; Dependabot alerts |

**Safe behaviour under malicious/unexpected inputs:**
1. LLM Guard blocks input before any LLM call is made — malicious input never reaches the model
2. If LLM Guard passes but governance detects anomaly → `governance_audit: flagged`; `requires_human_review: true`
3. If agent returns malformed JSON → schema validator raises `ValidationError`; mock fallback activates
4. If Gemini API fails → mock response activates; structured error logged; no crash
5. Rate limiter rejects flood attacks before they reach the agent layer

### 2.13 AI Lifecycle Automation

| Lifecycle Phase | Automated Step | Tool / Location |
|----------------|---------------|-----------------|
| **Development** | Type checking, lint, format | mypy, black, eslint (pre-commit hooks) |
| **Testing** | Unit, integration, security, governance tests | pytest CI; `test_agents.py`, `test_security.py`, `test_interview_coach.py` |
| **Security scanning** | Container vulnerability scan, SAST, secret detection | Trivy, Bandit, GitGuardian (CI) |
| **Build** | Docker image build (multi-stage, non-root) | `Dockerfile` in backend & frontend |
| **Registry** | Push versioned images with vulnerability report | GCP Artifact Registry; Trivy on push |
| **Deployment** | Cloud Run deployment on merge to main | `.github/workflows/gcp-deploy.yaml` |
| **Evaluation** | LLM-as-a-judge scoring on curated datasets | `evals/run_evals.py`; `eval-runner.yml` (manual dispatch) |
| **Monitoring** | Trace aggregation, cost, confidence trends | Langfuse dashboard; structured log pipeline |
| **Governance drift** | Governance test suite run weekly | GitHub Actions scheduled run |

Automation reduces development effort in these ways:
- Security and governance tests run on every PR — no manual audit needed before merge
- Mock mode eliminates real API dependency in CI, reducing cost and flakiness
- LLM-as-a-judge evaluation replaces laborious human review of every model response
- Structured logging and Langfuse tracing make debugging significantly faster

### 2.14 Implementation Effort Assessment

**Scope completed within project guidelines:**

| Component | Status |
|-----------|--------|
| 5 specialised agents (Extractor, ResumeCritic, ContentStrength, JobAlignment, InterviewCoach) | ✅ Complete |
| LangGraph orchestration with session state | ✅ Complete |
| SHARP Governance Service (bias, hallucination, confidence) | ✅ Complete |
| LLM Guard + Output Sanitizer security layer | ✅ Complete |
| FastAPI backend with rate limiting | ✅ Complete |
| React + TypeScript frontend | ✅ Complete |
| Langfuse distributed tracing | ✅ Complete |
| LLM-as-a-judge evaluation pipeline | ✅ Complete |
| Comprehensive test suite (42+ tests) | ✅ Complete |
| CI/CD pipeline (GCP Cloud Run) | ✅ Complete |
| Documentation (6 detailed docs + 3 READMEs) | ✅ Complete |

The implementation scope is comfortably within project guidelines. Governance, security, and evaluation features were built incrementally alongside core functionality, keeping each increment well within expected effort bounds.

---

## 3. System Architecture

### 2.1 Logical Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                  PRESENTATION LAYER (React)                    │
│              Multi-agent UI with workflow guidance              │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTPS
┌──────────────────────────────┴──────────────────────────────────┐
│                     API LAYER (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  POST /api/v1/chat       (Multi-intent orchestration)   │  │
│  │  GET  /api/v1/agents     (Agent registry & prompts)     │  │
│  │  GET  /api/v1/health     (System status & metrics)      │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────┐
│              ORCHESTRATION LAYER (LangGraph)                   │
│  Intent Router → Agent Dispatcher → State Manager              │
│  Features: Session persistence, multi-turn state, error recovery
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────┐
│                    AGENT LAYER                                  │
│                                                                 │
│  All agents extend BaseAgent with:                             │
│  • Prompt injection defense (LLM Guard)                        │
│  • Output sanitization & safety                               │
│  • Structured logging & Langfuse tracing                      │
│  • Mock response fallback                                      │
│                                                                 │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────┐    │
│  │ResumeCritic  │  │ContentStrength   │  │JobAlignment  │    │
│  └──────────────┘  └──────────────────┘  └──────────────┘    │
│  ┌──────────────────────────┐  ┌──────────────────────────┐   │
│  │InterviewCoach (Stateful) │  │ExtractorAgent            │   │
│  └──────────────────────────┘  └──────────────────────────┘   │
│                                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────┐
│                 INTEGRATION LAYER                               │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                   │
│  │Gemini LLM API    │  │Gemini Live API   │                   │
│  │(Text/Function)   │  │(Real-time Audio) │                   │
│  └──────────────────┘  └──────────────────┘                   │
│  ┌──────────────────┐  ┌─────────────────────┐                │
│  │LLM Guard Scanner │  │Output Sanitizer     │                │
│  │(Input Security)  │  │(Hallucination Check)│                │
│  └──────────────────┘  └─────────────────────┘                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │Langfuse (Distributed Tracing & Evaluation Platform)      │  │
│  │ - Session correlation · Trace aggregation · Cost tracking│  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │Structured Logging System (JSON output with context)      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────┐
│                  GOVERNANCE LAYER                               │
│                                                                 │
│  SHARP Governance Service Audits Every Agent Response:         │
│  • Hallucination Risk Assessment                              │
│  • Confidence Threshold Validation                            │
│  • Bias Flag Detection (protected attributes)                 │
│  • Content Strength Validation                                │
│  • Governance Metadata Generation                             │
│                                                                 │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Physical Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Google Cloud Platform                       │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Cloud Run (Containerized Microservices)                      │  │
│  │                                                              │  │
│  │  ┌─────────────────┬──────────────────┐                     │  │
│  │  │   Backend Pod   │  Frontend Pod    │                     │  │
│  │  │  (FastAPI)      │  (React SPA)     │                     │  │
│  │  │  Port 8000      │  Port 3000       │                     │  │
│  │  └────────┬────────┴────────┬─────────┘                     │  │
│  │           │                 │                                │  │
│  │           └─────────┬───────┘                                │  │
│  │                     │ Internal networking                    │  │
│  └─────────────────────┼──────────────────────────────────────┘  │
│                        │                                           │
│  ┌─────────────────────┴──────────────────────────────────────┐  │
│  │ External APIs & Services                                  │  │
│  │                                                            │  │
│  │ • Google Gemini API (LLM inference)                       │  │
│  │ • Langfuse (Observability SaaS)                          │  │
│  │ • Cloud Artifact Registry (Docker images)                │  │
│  │                                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ Cloud Load Balancer (HTTPS ingress, traffic distribution)  │  │
│  │ • SSL certificate management                              │  │
│  │ • Rate limiting & DDoS protection                         │  │
│  │ • Geographic routing                                       │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
         ▲                                              ▲
         │                                              │
         │                                              │
    ┌────┴──────┐                          ┌───────────┴────────┐
    │  Browser  │                          │  GitHub Actions    │
    │  (Client) │                          │  (CI/CD Pipeline)  │
    └───────────┘                          └────────────────────┘
```

### 2.3 Deployment Strategy

InterviewReady uses **containerized microservices architecture** on Google Cloud Run with containerized CI/CD workflows:

**Deployment Stages:**
1. **Local Development:** Docker Compose for local backend + frontend, mock responses enabled
2. **Staging:** GCP Cloud Run, real Gemini API, Langfuse tracing, dataset evaluation
3. **Production:** GCP Cloud Run with auto-scaling, advanced monitoring, PII redaction, rate limiting

**CI/CD Pipeline:**
```
Pull Request
  → Linting & Format Checks
  → Unit Tests (Python + TypeScript)
  → Integration Tests (API endpoints)
  → Security Scans (Trivy vulnerability scanning)
  → Build Docker images (Backend & Frontend)
  → Push to Artifact Registry
  → Deploy to Staging
  → Run evaluations on Langfuse datasets
  → Manual approval (if needed)
  → Deploy to Production
```

### 2.4 Data Flow & Integration Points

**Request Flow Sequence:**
```
User Input (Frontend)
  ↓ [Session ID validation]
API Gateway (/api/v1/chat)
  ↓ [Resume extraction + intent classification]
Orchestration Engine (LangGraph)
  ↓ [Route to appropriate agent(s)]
Agent Processing
  ├─ Input LLM Guard scan (prompt injection detection)
  ├─ PII redaction for sensitive data
  ├─ Construct and execute prompt
  ├─ Output sanitization
  ├─ Mock fallback if API fails
  ↓
SHARP Governance Audit
  ├─ Hallucination assessment
  ├─ Confidence threshold validation
  ├─ Bias flag detection
  ├─ Append governance metadata
  ↓
Response Aggregation + Tracing
  ├─ Attach decision_trace
  ├─ Package SHARP metadata
  ├─ Generate explanations
  ├─ Structured JSON logging
  ├─ Langfuse span submission
  ├─ Session state update
  ↓
Frontend Response & Rendering
```

**Integration Points:**

| Component | Purpose | Protocol | Failure Mode | SLA |
|-----------|---------|----------|--------------|-----|
| Google Gemini API | LLM inference & function calling | REST/gRPC | Mock fallback active | 99.9% |
| Langfuse | Distributed tracing & evaluation | gRPC | Silent (non-blocking) | 99.5% |
| LLM Guard | Prompt injection scanning | In-process library | Strict mode blocks input | N/A |
| Output Sanitizer | Hallucination detection | In-process library | Return sanitized output | N/A |

### 2.5 Architectural Justification

**Multi-Agent Architecture:** Each agent has distinct output formats, system prompts, and validation logic. Monolithic approach would be unmaintainable and reduce explainability.

**LangGraph Orchestration:** Declarative state graphs allow complex workflows (sequential, parallel, conditional routing) with built-in error handling, checkpointing, and audit trails vs. simple if-else routing which is inflexible and non-auditable.

**SHARP Governance Layer:** Applied post-agent-response ensures all agents are covered equally with consistent thresholds, preventing code duplication.

**Defense-in-Depth Security:** Multiple layers (LLM Guard → Output Sanitizer → Governance) catch different attack vectors rather than a single security layer that's easier to bypass.

**Session-State Management:** Multi-turn interview coaching requires maintaining question history, answer scores, and progression state across requests.

### 2.6 Technology Stack

| Layer | Technology | Version/Details | Justification |
|-------|-----------|-----------------|---------------|
| **Frontend** | React 18 + TypeScript | Latest | Type safety, modern hooks, concurrent features |
| |  Vite | 5.x | Fast build tool, HMR, optimized production builds |
| | TailwindCSS | 3.x | Utility-first styling, responsive design, dark mode support |
| | Vitest | Latest | Fast unit testing framework, Vite-native |
| **Backend** | Python | 3.11+ | Mature ecosystem, async/await support, scientific libraries |
| | FastAPI | 0.100+ | High performance, async support, automatic OpenAPI docs |
| | Pydantic V2 | 2.x | Type-safe validation, serialization, OpenAPI integration |
| | LangGraph | Latest | Stateful agent orchestration with checkpointing |
| | SQLAlchemy | 2.x | Async ORM, type hints, enterprise-grade |
| **LLM Services** | Google Gemini | Latest API | Function calling, structured outputs, live audio API |
| **Security** | LLM Guard | Latest | Prompt injection defense, input/output scanning |
| **Observability** | Langfuse | Cloud/OSS | LLM observability, distributed tracing, evaluations |
| | Structured Logging | JSON format | Machine-readable, context preservation, integration-friendly |
| **Infrastructure** | Google Cloud Run | Serverless | Auto-scaling, managed Kubernetes, cost-effective |
| | Docker | Latest | Containerization, reproducible deployments |
| | GitHub Actions | Latest | CI/CD workflows, secret management |

---

## 4. Agent System Design

### 3.1 ExtractorAgent

**Purpose & Responsibilities:**
- Converts resume PDF files into structured JSON Resume model data using LLM-powered extraction
- Parses PDF text content and maps it to standardized resume sections (work, education, skills, projects, awards, certificates)
- Validates extracted data for URL format, date structure, and field completeness
- Calculates confidence scores and identifies low-confidence fields requiring human review

**Planning/Reasoning:**
- Extracts text from PDF base64 payload using PDF parsing utilities
- Applies structured LLM prompting with strict JSON output requirements
- Validates URLs against source text to prevent hallucination
- Scores confidence based on completeness, uncertainty, validation errors, and structure quality
- Flags fields needing human review based on confidence thresholds

**Memory Mechanisms:**
- Session context preserves extracted resume data and confidence metrics
- Decision trace records extraction decisions and validation outcomes
- Langfuse traces maintain extraction audit trail with confidence scoring

**Tools Used:**
- Gemini LLM for intelligent text-to-structured-data extraction
- PDF parsing utilities for text extraction from base64 content
- JSON parser for structured output validation
- Validation utilities for URL, date, and field integrity checks
- Confidence scoring algorithm for quality assessment

### 3.2 ResumeCriticAgent

**Purpose & Responsibilities:**
- Analyzes resume structure and ATS (Applicant Tracking System) readability
- Evaluates formatting, content organization, and keyword optimization
- Provides markdown-formatted critique with improvement scores
- Identifies common resume pitfalls and formatting issues

**Planning/Reasoning:**
- Parses resume into logical sections (header, summary, experience, skills, education)
- Scores each section on clarity, ATS compatibility, and professional presentation
- Cross-references against ATS best practices and industry standards
- Generates prioritized recommendations based on impact

**Memory Mechanisms:**
- Session context preserves resume data and analysis history
- Decision trace records evaluation criteria and scoring rationale
- Langfuse traces maintain historical critiques for user reference

**Tools Used:**
- Gemini text API for evaluation and critique generation
- Text parsing utilities for resume section extraction
- Governance Service for confidence validation

### 3.3 ContentStrengthAgent

**Purpose & Responsibilities:**
- Evaluates skills, achievements, and content effectiveness
- Identifies strengths and quantifiable evidence from resume
- Scores content on impact, clarity, and relevance
- Suggests evidence-based improvements with specific examples

**Planning/Reasoning:**
- Extracts and categorizes skills (technical, soft, domain-specific)
- Analyzes achievements for quantifiable metrics and business impact
- Scores content strength on evidence quality and specificity
- Cross-references with job requirements for relevance

**Memory Mechanisms:**
- Session context maintains extracted skills and achievements database
- Confidence scores track certainty of skill extraction
- Decision trace documents evidence quality assessment

**Tools Used:**
- Gemini function calling for structured skill extraction
- NLI (Natural Language Inference) utilities for logic consistency
- JSON parser for structured output handling

### 3.4 JobAlignmentAgent

**Purpose & Responsibilities:**
- Performs semantic matching between resume and job description
- Calculates fit scores and identifies skill/experience gaps
- Prioritizes missing skills by criticality
- Provides JSON-structured alignment analysis

**Planning/Reasoning:**
- Parses job description for required skills, experience level, and qualifications
- Maps resume content to job requirements using semantic similarity
- Calculates match scores using evidence strength and relevance
- Identifies both explicit gaps and implicit misalignments

**Memory Mechanisms:**
- Session context caches parsed job description
- Similarity scores maintained for iterative analysis
- Decision trace records matching rationale and evidence sources

**Tools Used:**
- Gemini for semantic analysis and alignment computation
- Text embedding and similarity utilities
- Governance Service for confidence threshold validation

### 3.5 InterviewCoachAgent (Stateful)

**Purpose & Responsibilities:**
- Simulates role-specific interview via multi-turn conversation
- Asks tailored questions based on resume and job requirements
- Evaluates candidate answers in real-time
- Provides constructive feedback and progression guidance
- Maintains interview state across 5 questions with scoring

**Planning/Reasoning:**
- Analyzes resume to understand background and key talking points
- Reviews job description for critical competencies and questions
- Generates behavioral, technical, situational, and competency questions
- Progressively evaluates answers using defined rubrics
- Adapts follow-up questions based on answer quality

**Memory Mechanisms:**
- **Session State:** Maintains interview progress (current question #, total questions, scores)
- **Interview History:** Preserves all questions asked, answers provided, and feedback given
- **Progression Tracking:** Scores for each answer determine whether to advance or re-ask
- **Langfuse Tracing:** Complete interview arc with decision points and evaluator reasoning

**Tools Used:**
- Gemini for question generation and answer evaluation
- Evaluator specialized Gemini prompt for scoring and feedback
- Schema-constrained JSON for deterministic output
- LLM Guard for adversarial input detection
- Output Sanitizer for PII redaction in sensitive content
- Structured Logging for interview audit trail

---

## 5. Explainable & Responsible AI Practices

### 4.1 Development & Deployment Alignment

**Development Stage:**
- ✅ Agent responses include structured explainability fields (`feedback`, `reasoning`, `decision_trace`)
- ✅ Schema-constrained JSON keeps outputs predictable and inspectable
- ✅ Deterministic fallback scoring reduces silent failures
- ✅ Security tests cover prompt injection, adversarial input, PII redaction, bias detection
- ✅ All agents extend BaseAgent with consistent security/logging mixins

**Deployment Stage:**
- ✅ Every agent response audited by SHARP Governance Service post-orchestration
- ✅ CI enforces interview-agent and governance tests before production deployment
- ✅ Langfuse-compatible tracing supports full auditability and post-deployment monitoring
- ✅ Governance metadata merged into responses (not overwritten) for safety evidence preservation
- ✅ Environment variables distinguish local/staging/production for audit trail filtering

### 4.2 Fairness, Bias Mitigation & Explainability Approach

**Fairness:**
- **Protected Attribute Non-Inference:** Agent explicitly instructed never to infer protected attributes (age, gender, ethnicity, nationality) from resume
- **Job-Resume Anchoring:** Coaching remains anchored to evidence in resume, job description, and candidate answer—no external demographic data
- **Bias Pattern Detection:** Regex patterns scan job descriptions for biased language and surface flags through governance metadata
- **Multi-Agent Consensus:** Different agents evaluate same input; scoring disagreements indicate potential fairness issues

**Bias Mitigation:**
- **Prompt Engineering:** All system prompts include explicit anti-bias directives (see `ANTI_JAILBREAK_DIRECTIVE` in interview coach)
- **Confidence Thresholds:** Low-confidence responses flagged for human review before presentation
- **Governance Overrides:** Hallucination/bias signals trigger `requires_human_review` flag
- **Redaction:** Direct identifiers (SSN, email, phone) redacted before LLM calls; candidates see redacted feedback

**Explainability:**
- **Decision Trace:** Every response includes `decision_trace` array documenting reasoning steps
- **Reasoning Field:** Agent includes `reasoning` explaining the approach taken and validation applied
- **Confidence Scores:** Each decision accompanied by `confidence_score` (0.0-1.0) indicating certainty
- **SHARP Metadata:** Structured governance audit data accompanies responses (hallucination flags, bias indicators, content validation results)
- **Langfuse Traces:** Full traceability of inputs, processing steps, and outputs available for post-analysis

### 4.3 IMDA Model AI Governance Framework Alignment

InterviewReady aligns with IMDA's Model AI Governance Framework across four pillars:

**1. Internal Governance Structures & Measures**
- Agent-specific risks, mitigations, and Responsible AI metadata attached to every response
- CI pipeline enforces interview-agent and governance tests before production deployment
- SHARP Governance Service serves as internal audit layer
- Environment-aware configuration distinguishes development/staging/production for governance controls

**2. Human Involvement in AI-Augmented Decision-Making**
- Interview agent provides coaching support only—does not take autonomous employment actions
- `requires_human_review` flag escalates sensitive, biased, or adversarial cases
- Governance metadata enables human reviewers to understand reasoning behind agent recommendations
- Explanative fields (`feedback`, `reasoning`, `decision_trace`) support informed human judgment

**3. Operations Management**
- Untrusted user text screened for prompt injection before model execution
- PII redaction applied to sensitive data before LLM calls
- Post-response governance audits validate and preserve safety metadata
- Fallback mechanisms ensure graceful degradation (mock responses when API unavailable)
- Structured logging and Langfuse tracing enable operational visibility and anomaly detection

**4. Stakeholder Interaction & Communication**
- Users receive explainable fields enabling self-service understanding of agent reasoning
- Reviewers receive decision traces, governance metadata, and confidence scores for audit
- Transparency reports can be generated from Langfuse traces showing decision patterns
- No claims of autonomous hiring capability—positioning as advisory tool only

---

## 6. AI Security Risk Register

### 5.1 Identified Risks & Mitigation Strategies

| Risk ID | Risk Category | Description | Severity | Likelihood | Mitigation Strategy | Security Control | Validation |
|---------|---------------|-------------|----------|------------|--------------------|--------------------|-----------|
| **SEC-001** | Prompt Injection | Malicious user inputs in resume/interview answers attempt to override system prompt or reveal hidden instructions | HIGH | MEDIUM | Pattern matching for jailbreak attempts; LLM Guard scanning; strict input validation | `InterviewCoachAgent.PROMPT_INJECTION_PATTERNS` regex; LLM Guard scanner; schema validation | Unit tests: `test_interview_coach.py` |
| **SEC-002** | PII Exposure | Sensitive data (SSN, email, phone) in resume or interview context exposed via LLM output or Langfuse traces | HIGH | MEDIUM | PII redaction before LLM calls; secure trace filtering; output sanitizer | `InterviewCoachAgent.SENSITIVE_PATTERNS`; output sanitizer; Langfuse filtering | Integration tests verify redaction |
| **SEC-003** | Hallucination | Model generates information not supported by source documents (resume/JD) | MEDIUM | HIGH | Confidence threshold validation; hallucination risk assessment; NLI consistency checks | `SharpGovernanceService.hallucination_risk_assessment()`; confidence scoring | Governance tests validate thresholds |
| **SEC-004** | Bias Injection via Job Description | Biased language in job description (age, gender, nationality signals) influences agent recommendations | MEDIUM | MEDIUM | Bias pattern detection; protected attribute non-inference; governance flags | `InterviewCoachAgent.BIAS_PATTERNS`; governance metadata; human review escalation | Bias detection regex tests |
| **SEC-005** | Model Tampering | Attacker attempts to manipulate model responses via API hijacking or response interception | HIGH | LOW | HTTPS encryption; API key management; response signature validation | CloudRun native HTTPS; environment-based API key injection; Langfuse trace validation | TLS 1.2+ enforced; security scans |
| **SEC-006** | API Key Leakage | Gemini or Langfuse API keys exposed in logs, git history, or client-side code | CRITICAL | MEDIUM | Environment variable isolation; secret management via GitHub Secrets; no logging of API keys | `settings.GEMINI_API_KEY` via `.env`; GitHub Secrets injection; audit logging | Git history scanning; dependency audit |
| **SEC-007** | Unauthorized Session Access | User accesses another user's session data or interview history | MEDIUM | LOW | Session ID validation; user authentication; session ownership checks | Session ownership verification in API layer; Firebase Auth integration (if configured) | API endpoint tests verify ownership |
| **SEC-008** | Data Exfiltration via Traces | Sensitive data inadvertently captured in Langfuse traces accessible to unauthorized users | MEDIUM | MEDIUM | Trace filtering; PII redaction in trace metadata; access control on Langfuse dashboard | Redaction applied before trace submission; RBAC on Langfuse organization | Audit trace content; verify field filtering |
| **SEC-009** | Prompt Injection via Job Description | JD content contains injected instructions attempting to modify agent behavior | MEDIUM | MEDIUM | Input sanitization; schema validation; LLM Guard scanning of JD | LLM Guard on JD input; output sanitizer on agent responses | Security tests with adversarial JD |
| **SEC-010** | Rate Limiting Bypass | Attacker floods API endpoints to cause DoS or exhaust API quota | MEDIUM | MEDIUM | API rate limiting; CloudRun auto-scaling limits; request throttling | Implemented via `app/core/limiter.py`; CloudRun concurrency controls | Load testing; rate limit verification |
| **SEC-011** | Compliance Drift | Agent behavior diverges from fairness/explainability standards over time | LOW | MEDIUM | Continuous testing; governance test suite; Langfuse trend monitoring | Weekly governance test runs; prompt versioning tracking | Test coverage metrics; trend dashboard |
| **SEC-012** | Supply Chain Attack | Dependency vulnerability in pip/npm packages | MEDIUM | MEDIUM | Dependency scanning; pinned versions; security updates SLA | Trivy scans in CI; `pyproject.toml` version pinning; GitHub Dependabot | Container image scans |

### 5.2 Security Controls & Testing

**Input Security Controls:**
```python
# LLM Guard Scanning (all agents via BaseAgent)
with langfuse.trace(name="llm_guard_scan"):
    guard_result = llm_guard_scanner.scan_prompt(user_input)
    if guard_result.unsafe:
        block_request_and_log(guard_result.violation_types)
        return error_response("Input contains suspicious patterns")

# PII Redaction (InterviewCoachAgent)
redacted_input = redact_pii(user_input, SENSITIVE_PATTERNS)
# Use redacted_input for prompt construction
```

**Output Security Controls:**
```python
# Output Sanitization (all agents via BaseAgent)
sanitized_output = output_sanitizer.sanitize(model_response)

# Governance Auditing (post-orchestration)
governance_audit = sharp_governance_service.audit(
    agent_response=agent_response,
    user_input=user_input,
    context=session_context
)
if governance_audit.requires_review:
    flag_for_human_review(governance_audit)
```

**CI/CD Security Integration:**
```yaml
# GitHub Actions workflow includes:
- Trivy container vulnerability scanning
- SAST linting (Python/TypeScript)
- Dependency auditing
- Interview & governance tests (before build)
- SonarQube code quality checks (optional)
```

---

## 7. MLSecOps/LLMSecOps Pipeline

### 6.1 Pipeline Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LLM OPERATIONS PIPELINE                             │
└─────────────────────────────────────────────────────────────────────────────┘

DEVELOPMENT → TESTING → SECURITY → BUILD → REGISTRY → DEPLOY → MONITOR
     ↓           ↓           ↓         ↓       ↓         ↓        ↓
     
┌─────────┬──────────────────────────────────────────────────────────────────┐
│ Git PR  │  Code Review & Analysis                                          │
├─────────┼──────────────────────────────────────────────────────────────────┤
│ 1. Lint │  • Python (black, pylint, mypy)                                 │
│ 2. Type │  • TypeScript (eslint, tsc)                                     │
│ 3. FOC  │  • Security patterns (pre-commit hooks)                         │
└─────────┴──────────────────────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────────────────────────────────┐
│ UNIT TESTING                                                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│ • Agent tests (mock responses, prompt templates)                            │
│ • API endpoint tests (request/response validation)                          │
│ • Governance service tests (bias detection, confidence thresholds)          │
│ • Security tests (prompt injection patterns, PII redaction)                 │
│ • Orchestration tests (multi-agent routing, state management)               │
└──────────────────────────────────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────────────────────────────────┐
│ INTEGRATION TESTING                                                          │
├──────────────────────────────────────────────────────────────────────────────┤
│ • End-to-end interview flow (5-question progression)                        │
│ • Multi-agent workflows (concurrent agent execution)                        │
│ • Governance audit integration (response → audit → client)                  │
│ • Session state persistence (multi-turn conversation)                       │
│ • API contract validation (OpenAPI schema enforcement)                      │
└──────────────────────────────────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────────────────────────────────┐
│ SECURITY SCANNING                                                            │
├──────────────────────────────────────────────────────────────────────────────┤
│ • SAST (Static Application Security Testing)                               │
│   - Bandit (Python security issues)                                        │
│   - ESLint security plugins (TypeScript/JavaScript)                        │
│ • Dependency Scanning                                                       │
│   - Trivy (known vulnerabilities in packages)                              │
│   - Snyk (deeper dependency analysis)                                      │
│ • Secret Scanning                                                           │
│   - GitGuardian (API key detection in git history)                         │
│   - Pre-commit hooks (local secret detection)                              │
│ • LLM-Specific Validation                                                   │
│   - Prompt injection test suite (SEC-001 validation)                       │
│   - Bias detection tests (SEC-004 validation)                              │
│   - PII redaction tests (SEC-002 validation)                               │
└──────────────────────────────────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────────────────────────────────┐
│ DOCKER BUILD & IMAGE SECURITY                                               │
├──────────────────────────────────────────────────────────────────────────────┤
│ • Multi-stage builds (minimize final image size)                            │
│ • Non-root user execution (least privilege)                                 │
│ • Image layer scanning (vulnerabilities in base images)                     │
│ • Signed container images (supply chain security)                           │
└──────────────────────────────────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────────────────────────────────┐
│ ARTIFACT REGISTRY                                                            │
├──────────────────────────────────────────────────────────────────────────────┤
│ • Images pushed: backend:<commit-sha>, frontend:<commit-sha>                │
│ • Vulnerability scanning on push (Trivy integration)                        │
│ • Access control via service account (GCP IAM)                              │
│ • Image retention policy (cleanup old builds)                               │
└──────────────────────────────────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────────────────────────────────┐
│ CLOUD RUN DEPLOYMENT                                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ • Service Account (minimal IAM permissions)                                 │
│ • Secrets injection (Gemini API key from Secret Manager)                    │
│ • Network policy (VPC connector if needed)                                  │
│ • Auto-scaling (based on concurrency, CPU)                                 │
│ • HTTPS enforced (TLS 1.2+)                                                 │
│ • Health checks (readiness/liveness probes)                                 │
└──────────────────────────────────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────────────────────────────────┐
│ POST-DEPLOYMENT EVALUATION & MONITORING                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│ • Langfuse Dataset Evaluation                                               │
│   - Run agent evaluations on test cases                                     │
│   - LLM-as-a-judge scoring (hallucination, bias, quality)                   │
│   - Human-in-the-loop verification for edge cases                           │
│ • Real-Time Monitoring                                                      │
│   - Langfuse dashboards (trace volume, latency, cost)                       │
│   - Confidence score trends (alert if dropping)                             │
│   - Governance audit signals (bias flags, review escalations)               │
│   - API error rates & latency (SLO tracking)                                │
│ • Incident Response                                                         │
│   - Automated alerts for governance violations                              │
│   - Rollback procedures (blue-green deployment)                             │
│   - Post-mortems on security events                                         │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 LLMSecOps Pipeline Description

The pipeline integrates LLM-specific security checks throughout the software development lifecycle:

**1. Development Phase**
- Developers write agents with built-in security (BaseAgent mixin applies LLM Guard, sanitizers)
- Pre-commit hooks catch accidental API key commits
- Type hints enforce input/output contracts

**2. Testing Phase**
- Unit tests validate LLM-specific behaviors (function calling, JSON parsing, prompt consistency)
- Security tests validate adversarial inputs (prompt injection, bias patterns, PII redaction)
- Orchestration tests validate multi-agent workflows and governance integration

**3. Security Scanning Phase**
- SAST tools identify code vulnerabilities
- Dependency scanning finds known CVEs
- LLM-specific scanning validates prompt templates for injection vectors

**4. Build Phase**
- Docker images built with minimal layers and non-root execution
- Image scanned for vulnerabilities before registry push

**5. Registry Phase**
- Images stored in secured Artifact Registry with access controls
- Vulnerability scanning triggers alerts for critical issues

**6. Deployment Phase**
- Secrets managed via GCP Secret Manager (never in code/env files)
- Service accounts have minimal IAM permissions (least privilege)
- HTTPS enforced; health checks validate deployment readiness

**7. Monitoring Phase**
- Langfuse traces capture all LLM calls with inputs/outputs/costs
- Governance audit signals flag anomalies (low confidence, bias patterns, potential hallucinations)
- Automated alerts escalate security events for human review

---

## 8. Testing Summary

### 7.1 Types of Tests Performed

| Test Type | Framework | Location | Coverage | Purpose |
|-----------|-----------|----------|----------|---------|
| **Unit Tests** | pytest | `backend/tests/test_agents.py` | Agent logic, response generation | Validates individual agent behavior in isolation |
| | pytest | `backend/tests/test_orchestration_governance.py` | Orchestration routing, governance audits | Validates orchestration logic and governance integration |
| | pytest | `backend/tests/test_agent_structural_checks.py` | Schema validation, JSON structure | Ensures agents output valid structured responses |
| | vitest | `frontend/tests/backendService.test.js` | API client functionality | Validates frontend integration with backend API |
| **Integration Tests** | pytest | `backend/tests/test_api_endpoints.py` | API endpoints, request/response flow | Tests end-to-end API request handling |
| | pytest | `backend/tests/test_interview_coach.py` | Multi-turn interview flow, state management | Tests stateful interview coach across turns |
| | pytest | `backend/tests/test_agent_evals.py` | Agent evaluations on Langfuse datasets | Tests agent quality on realistic scenarios |
| **Security Tests** | pytest | `backend/tests/test_interview_coach.py` | Prompt injection, PII redaction, bias patterns | Validates security mitigations for agent input/output |
| | pytest | In CI workflow | Trivy scanning, SAST, secret detection | Validates container and code security pre-deployment |
| **Governance Tests** | pytest | `backend/tests/test_orchestration_governance.py` | SHARP governance audit, confidence thresholds, bias flags | Validates governance layer post-orchestration |
| **Evaluation Tests** | Custom runner | `evals/run_evals.py` | LLM-as-a-judge scoring, human review | Validates agent quality on curated datasets |

### 7.2 Test Results & Coverage

**Test Execution (Local):**
```bash
# Unit tests
$ uv run pytest backend/tests/ -v

# With coverage
$ uv run pytest backend/tests/ --cov=app --cov-report=html

# Specific test class
$ uv run pytest backend/tests/test_interview_coach.py -v

# Interview coach security tests
$ uv run pytest backend/tests/test_interview_coach.py::test_prompt_injection_defense -v
```

**CI Test Pipeline:**
```bash
# Automatic on every pull request
- Lint & type checks: ~2 minutes
- Unit tests: ~5 minutes
- Integration tests: ~10 minutes
- Security scans: ~3 minutes
- Total: ~20 minutes (before deployment candidate can merge)
```

**Current Test Coverage (Backend):**
- **Agent Logic:** >85% statement coverage
- **Orchestration & Governance:** >80% statement coverage
- **API Endpoints:** >75% statement coverage
- **Security Validation:** 100% (all prompt injection patterns tested)

**Example Test Results:**
```
test_agents.py::test_resume_critic_parsing ✓
test_agents.py::test_content_strength_extraction ✓
test_agents.py::test_job_alignment_scoring ✓
test_interview_coach.py::test_five_question_progression ✓
test_interview_coach.py::test_prompt_injection_patterns_blocked ✓
test_interview_coach.py::test_pii_redaction ✓
test_interview_coach.py::test_bias_pattern_detection ✓
test_orchestration_governance.py::test_hallucination_detection ✓
test_orchestration_governance.py::test_confidence_thresholds ✓
test_api_endpoints.py::test_chat_api_intent_routing ✓
test_api_endpoints.py::test_session_state_persistence ✓

### Operations & Monitoring

**Monitoring Tools:**
- **Langfuse Dashboard:** Trace distribution, token costs, latency
- **Cloud Run Console:** Deployment status, container logs, scaling metrics
- **CloudWatch:** Infrastructure metrics, alerts

**Key Metrics:**
- Average latency per agent type
- Inference cost per session
- Confidence score distribution
- Governance audit signals (bias flags, review escalations)
- API error rates

**Troubleshooting:**
- View backend logs: GCP Cloud Run console → Logs tab
- View frontend errors: Browser DevTools console
- Check Langfuse traces: Langfuse dashboard → Traces tab

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for detailed infrastructure setup and operations.

---

## Documentation

Comprehensive project documentation is available in the [`docs/`](docs/) directory:

| Document | Description |
|----------|-------------|
| [`docs/LOGICAL_DIAGRAM.md`](docs/LOGICAL_DIAGRAM.md) | **Full logical architecture diagram** — 8-layer diagram, component interaction, 3 data-flow paths (REST / WebSocket / Eval), session state schema, and per-layer design justification |
| [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md) | Physical/infrastructure architecture, GCP deployment topology, CI/CD pipeline, integration points, and technology stack rationale |
| [`docs/AGENT_DESIGN.md`](docs/AGENT_DESIGN.md) | Internal logic, reasoning patterns, memory mechanisms, prompt design, and inter-agent communication for each of the 5 agents |
| [`docs/RESPONSIBLE_AI.md`](docs/RESPONSIBLE_AI.md) | Fairness, bias mitigation, explainability, HITL escalation, PII protection, and SHARP governance framework (IMDA alignment) |
| [`docs/SECURITY_RISK_REGISTER.md`](docs/SECURITY_RISK_REGISTER.md) | AI security risk register: prompt injection, hallucination, PII leakage, bias injection, supply chain — with per-risk severity and mitigation |
| [`docs/MLSECOPS_PIPELINE.md`](docs/MLSECOPS_PIPELINE.md) | MLSecOps / LLMSecOps pipeline: CI/CD automation, security scanning, model versioning, evaluation, monitoring |

- **[Backend Setup](backend/README.md)** — Python server, agent configuration, API reference
- **[Frontend Setup](frontend/README.md)** — React application setup and API integration

---

**Last Updated:** March 2026  
**Stable Release:** v1.0

**Edge Cases:**
```bash
uv run python -m evals.run_evals --agent InterviewCoachAgent --edge-cases --max-cases 3
```

**All Agents with Langfuse Tracking:**
```bash
uv run python -m evals.run_evals --langfuse-dataset interviewready_cases --max-cases 1
```

### Available Agents for Evaluation
- `ResumeCriticAgent` — ATS & formatting analysis
- `ContentStrengthAgent` — Skill & achievement effectiveness
- `JobAlignmentAgent` — Resume-to-JD matching
- `InterviewCoachAgent` — Interview preparation & coaching

### Options
- `--agent` — Comma-separated agent names
- `--max-cases` — Limit test cases
- `--edge-cases` — Run edge case scenarios
- `--run-name` — Custom Langfuse run identifier

## 🔐 Security & Compliance

- ✅ **Prompt Injection Defense** — LLM Guard input scanning
- ✅ **Output Sanitization** — Hallucination & leakage detection
- ✅ **PII Redaction** — GDPR-compliant data masking
- ✅ **Bias Detection** — Protected attribute recognition & fairness flags
- ✅ **Auditable Decisions** — Complete trace of reasoning & changes
- ✅ **Governance Checks** — Confidence thresholds & hallucination risk assessment

See [ARCHITECTURE.md](./ARCHITECTURE.md#security--risk-mitigation) for comprehensive security controls and risk mitigation strategies.

## 🏃 Development Workflow

### Setup Local Environment

```bash
# Backend
cd backend
uv sync
cp .env.example .env
# Update .env with GEMINI_API_KEY, etc.

# Frontend
cd frontend
npm install
```

### Run Backend Locally

```bash
cd backend
uv run python -m app.main
# API available at http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Run Tests

```bash
cd backend

# All tests
uv run pytest

# Unit tests only
uv run pytest backend/tests/ -k "not integration"

# Security tests
uv run pytest backend/tests/ -k "security or injection or sanitiz"

# With coverage
uv run pytest --cov=app
```

### Mock Mode (Development)

Enable in `.env` or `config.py`:
```
MOCK_INTERVIEW_COACH_AGENT=true
MOCK_CONTENT_STRENGTH_AGENT=false
MOCK_JOB_ALIGNMENT_AGENT=false
MOCK_RESUME_CRITIC_AGENT=false
```

## 📊 Monitoring & Analytics

- **[Langfuse Dashboard](https://cloud.langfuse.com)** — LLM traces, cost tracking, performance metrics
- **Structured Logs** — JSON format with session, agent, timing, and error context
- **Decision Traces** — Agent-level decision path auditing
- **Governance Metadata** — Bias flags, hallucination scores, confidence metrics

## 🤝 Contributing

See [AGENTS.md](./.agents/README.md) for agent customization guidelines and roam-based codebase navigation.

## 📦 Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Tailwind CSS |
| Backend | FastAPI + Uvicorn + Pydantic v2 |
| LLM | Google Gemini API 2.5 Flash |
| Orchestration | LangGraph |
| Security | LLM Guard Scanner + Output Sanitizer |
| Observability | Langfuse + Structured JSON Logging |
| Testing | pytest + pytest-asyncio |
| Deployment | Docker + Cloud Run / K8s |
| Package Manager | uv |

For detailed rationale and architecture justification, see [ARCHITECTURE.md](./ARCHITECTURE.md#technology-stack).

## 📄 License

[Add your license here]

## 👥 Support

For architecture questions, refer to [ARCHITECTURE.md](./ARCHITECTURE.md).  
For API issues, see [backend/README.md](backend/README.md).  
For UI issues, see [frontend/README.md](frontend/README.md).

- `--langfuse-dataset` - Specify Langfuse dataset name
- `--sync-langfuse-dataset` - Upload local cases to Langfuse

### Evaluation Datasets

#### Regular Datasets
- `evals/datasets/resumes.json` - Standard resume fixtures
- `evals/datasets/job_descriptions.json` - Standard job descriptions
- `evals/datasets/histories.json` - Standard conversation histories
- `evals/datasets/cases.json` - Standard evaluation cases

#### Edge Case Datasets
- `evals/datasets/edge_case_resumes.json` - Edge case resume fixtures
- `evals/datasets/edge_case_jobs.json` - Edge case job descriptions
- `evals/datasets/edge_case_histories.json` - Edge case conversation histories
- `evals/datasets/edge_case_cases.json` - Edge case evaluation scenarios

#### Edge Case Categories
- **No Resume Data**: Empty resumes, missing critical fields
- **Prompt Injection**: System override attempts, jailbreak attempts
- **Irrelevant Data**: Recipe content, code snippets instead of professional content
- **Context Flooding**: Extremely long resumes, massive job descriptions, long histories
- **Data Quality**: Malformed data, mixed languages, special characters
- **Edge Scenarios**: Missing job descriptions, contradictory information

### Langfuse Integration

Results are automatically tracked in Langfuse when `LANGFUSE_PUBLIC_KEY` is configured. Separate datasets can be synced:

```bash
# Sync regular cases
uv run python -m evals.run_evals --sync-langfuse-dataset "interviewready-regular"

# Sync edge cases  
uv run python -m evals.run_evals --edge-cases --sync-langfuse-dataset "interviewready-edge-cases"
```

## Deployment

### Local Development
```bash
docker-compose up --build --build-arg VITE_API_BASE_URL=localhost:8080
```
- Frontend: `http://localhost:80`
- Backend: `http://localhost:8080`

### Production Deployment
Automated deployment to GCP Cloud Run via GitHub Actions. See `.github/workflows/gcp-deploy.yaml` for configuration details.
