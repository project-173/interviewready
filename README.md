# InterviewReady: AI-Powered Resume & Interview Optimization Platform

An intelligent multi-agent AI system for comprehensive resume optimization and interview preparation, aligned with IMDA explainable and responsible AI governance principles.

---

## Table of Contents

1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Agent System Design](#agent-system-design)
4. [Explainable & Responsible AI Practices](#explainable--responsible-ai-practices)
5. [AI Security Risk Register](#ai-security-risk-register)
6. [MLSecOps/LLMSecOps Pipeline](#mlsecopsllmsecops-pipeline)
7. [Testing Summary](#testing-summary)
8. [Quick Start Guide](#quick-start-guide)
9. [Deployment & Operations](#deployment--operations)

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

## 2. System Architecture

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
│  │InterviewCoach (Stateful) │  │Extractor (Normalization)│   │
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

## 3. Agent System Design

### 3.1 ResumeCriticAgent

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

### 3.2 ContentStrengthAgent

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

### 3.3 JobAlignmentAgent

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

### 3.4 InterviewCoachAgent (Stateful)

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

## 4. Explainable & Responsible AI Practices

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

## 5. AI Security Risk Register

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

## 6. MLSecOps/LLMSecOps Pipeline

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

## 7. Testing Summary

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

================================ PASSED: 42/42 ================================
```

---

## 8. Quick Start Guide

For detailed setup instructions, see:
- **[Backend Setup](backend/README.md)**  
- **[Frontend Setup](frontend/README.md)**  
- **[Deployment Guide](DEPLOYMENT.md)**

### Prerequisites

- **Backend:** Python 3.11+, uv package manager, Google Gemini API key
- **Frontend:** Node.js 18+, npm or yarn
- **Docker:** (Optional) For containerized development
- **GCP Project:** (Optional) For cloud deployment

### Local Development

**1. Backend:**
```bash
cd backend
uv sync
cp .env.example .env
# Edit .env with your GEMINI_API_KEY
uv run python -m app.main
# http://localhost:8000/docs
```

**2. Frontend:**
```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

**3. Run Tests:**
```bash
cd backend
uv run pytest tests/ -v
```

---

## 9. Deployment & Operations

### Deployment Strategy

InterviewReady deploys as containerized microservices on Google Cloud Run:

**Stages:**
1. **Local Development** - Docker Compose with mock responses
2. **Staging** - Cloud Run with real Gemini API, Langfuse tracing
3. **Production** - Cloud Run with auto-scaling, monitoring, PII redaction

**Setup:**
```bash
# Set GitHub Secrets
GCP_PROJECT_ID          # Your GCP project
GCP_SA_KEY              # Service account JSON key
GOOGLE_AI_API_KEY       # Gemini API key
LANGFUSE_PUBLIC_KEY     # Langfuse credentials (optional)
```

**Deploy:**
```bash
git push origin main
# GitHub Actions triggers automatic deployment
# Logs visible in GitHub Actions tab
```

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

## Additional Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** — Comprehensive technical architecture & design rationale
- **[GOVERNANCE.md](./GOVERNANCE.md)** — SHARP governance framework & decision tracing
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** — Cloud Run, Docker, Kubernetes deployment options
- **[Backend README](backend/README.md)** — API documentation & backend configuration
- **[Frontend README](frontend/README.md)** — React build & integration guide
- **[Responsible AI](docs/interview-agent-responsible-ai.md)** — IMDA alignment & security mitigations
- **[Interview Coach Modifications](INTERVIEW_COACH_MODIFICATION.md)** — Customization guide

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

## Documentation

Comprehensive project documentation is available in the [`docs/`](docs/) directory:

| Document | Description |
|----------|-------------|
| [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md) | Logical and physical architecture, infrastructure, data flow, and technology justification |
| [`docs/AGENT_DESIGN.md`](docs/AGENT_DESIGN.md) | Internal logic, reasoning patterns, memory mechanisms, prompt design, and inter-agent communication for each agent |
| [`docs/RESPONSIBLE_AI.md`](docs/RESPONSIBLE_AI.md) | Fairness, bias mitigation, explainability, HITL, privacy, and governance framework (SHARP) |
| [`docs/SECURITY_RISK_REGISTER.md`](docs/SECURITY_RISK_REGISTER.md) | AI security risk register covering prompt injection, hallucination, data leakage, and mitigation strategies |
| [`docs/MLSECOPS_PIPELINE.md`](docs/MLSECOPS_PIPELINE.md) | MLSecOps / LLMSecOps pipeline design: CI/CD, automated AI security tests, model versioning, monitoring, and logging |
| [`docs/PRD.md`](docs/PRD.md) | Product Requirements Document |

## Deployment

### Local Development
```bash
docker-compose up --build --build-arg VITE_API_BASE_URL=localhost:8080
```
- Frontend: `http://localhost:80`
- Backend: `http://localhost:8080`

### Production Deployment
Automated deployment to GCP Cloud Run via GitHub Actions. See `.github/workflows/deploy.yml` for configuration details.
