# System Architecture Document — InterviewReady

## 1. Executive Summary

InterviewReady is a **multi-agent AI system** that helps candidates optimise their resumes and prepare for interviews. It exposes a stateful RESTful API backed by four specialised AI agents orchestrated via LangGraph, with a React single-page application as the front end. All agent decisions are traced through Langfuse, and a governance layer enforces confidence thresholds and hallucination checks before any response is returned to the user.

---

## 2. Logical Architecture

### 2.1 Layered View

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                       │
│  React 18 + TypeScript  ·  Tailwind CSS  ·  Vite            │
│  (HITL approval UI, workflow indicators, chat interface)     │
└──────────────────────────────┬──────────────────────────────┘
                               │  HTTPS (REST + JSON)
┌──────────────────────────────▼──────────────────────────────┐
│                       API Layer                              │
│  FastAPI · Pydantic v2 · CORS middleware                     │
│  /api/v1/chat  ·  /api/v1/agents  ·  /api/v1/sessions       │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                  Orchestration Layer                         │
│  LangGraph (StateGraph)  ·  OrchestrationAgent              │
│  Intent routing · HITL gates · Context propagation          │
└──────┬─────────────┬─────────────┬──────────────┬───────────┘
       │             │             │              │
┌──────▼──┐  ┌───────▼──┐  ┌──────▼─────┐  ┌────▼────────────┐
│ Resume  │  │ Content  │  │    Job     │  │  Interview      │
│ Critic  │  │ Strength │  │ Alignment  │  │  Coach          │
│ Agent   │  │  Agent   │  │  Agent     │  │  Agent          │
└──────┬──┘  └───────┬──┘  └──────┬─────┘  └────┬────────────┘
       └─────────────┴─────────────┴──────────────┘
                               │  Gemini API calls
┌──────────────────────────────▼──────────────────────────────┐
│                   AI Model Layer                             │
│  GeminiService  ·  MockGeminiService (dev/test)             │
│  google-generativeai (gemini-2.5-flash)                     │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│               Governance & Security Layer                    │
│  SharpGovernanceService · LLMGuardScanner                   │
│  OutputSanitizer · ConfidenceThreshold · HallucinationCheck │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│              Observability & Persistence Layer               │
│  Langfuse (tracing, cost, prompts) · SQLite checkpointer    │
│  In-memory SessionStore · Structured JSON logging           │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **React SPA** | Upload resumes, submit job descriptions, approve/reject HITL suggestions, display interview coaching UI |
| **FastAPI** | Request routing, schema validation, CORS, request-size enforcement, session context binding |
| **OrchestrationAgent** | Translate intent to agent sequence, run LangGraph workflow, propagate state |
| **ResumeCriticAgent** | ATS readability score, formatting recommendations, structural suggestions |
| **ContentStrengthAgent** | Skill identification, achievement evidence strength, faithful rephrasing suggestions |
| **JobAlignmentAgent** | Semantic resume–JD matching, keyword gap analysis, alignment report |
| **InterviewCoachAgent** | Role-specific question generation, candidate response evaluation, feedback loop |
| **GeminiService** | Gemini API wrapper, retry logic, token management |
| **SharpGovernanceService** | Hallucination risk scoring, confidence threshold enforcement, audit metadata |
| **LLMGuardScanner** | Prompt-injection detection (input), sensitive-content detection (output) |
| **Langfuse** | Distributed tracing per session, cost tracking, prompt versioning |

---

## 3. Physical / Infrastructure Architecture

### 3.1 Deployment Topology (Production — GCP)

```
Internet
   │
   ├── HTTPS ──► Cloud Run: interviewready-frontend (React)
   │                             │
   │                             │ HTTPS REST
   │                             ▼
   └──────────────────► Cloud Run: interviewready-backend (FastAPI)
                                  │
                         ┌────────┴────────┐
                         │                 │
                    Gemini API        Langfuse Cloud
                 (google.com)      (cloud.langfuse.com)
```

### 3.2 Infrastructure Components

| Resource | Type | Region | Purpose |
|----------|------|--------|---------|
| `interviewready-backend` | Cloud Run service | asia-southeast1 | FastAPI application, 4 GiB RAM |
| `interviewready-frontend` | Cloud Run service | asia-southeast1 | Nginx-served React SPA |
| `interviewready-repo` | Artifact Registry | asia-southeast1 | Docker image storage |
| `github-deployer` | GCP Service Account | — | CI/CD deployment identity |
| Gemini API | External managed service | google.com | LLM inference |
| Langfuse Cloud | External managed service | cloud.langfuse.com | Observability |

### 3.3 Containerisation

- **Backend** (`backend/Dockerfile`): Python image with `uv` for fast dependency resolution; exposes port 8080.
- **Frontend** (`frontend/Dockerfile`): Multi-stage build (Node.js build → Nginx serve); exposes port 80.
- Both images are AMD64-targeted for Cloud Run compatibility.

---

## 4. Service Deployment Strategy

### 4.1 CI/CD Pipeline (GitHub Actions — `.github/workflows/deploy.yml`)

```
Push to main / CICD / langfuse / security
          │
          ▼
  security-scan (Trivy FS scan)
          │
          ▼
  build-backend
    ├─ docker build backend image
    ├─ Trivy container scan
    └─ push to Artifact Registry
          │
          ▼
  deploy-backend (Cloud Run)
          │
          ▼
  build-frontend
    ├─ inject BACKEND_URL as build arg
    ├─ docker build frontend image
    ├─ Trivy container scan
    └─ push to Artifact Registry
          │
          ▼
  deploy-frontend (Cloud Run, --allow-unauthenticated)
```

### 4.2 Environment Strategy

| Environment | Branch | `APP_ENV` | Mock Agents | Langfuse |
|-------------|--------|-----------|-------------|---------|
| Local | any | `local` | Optional via `.env` | Optional |
| Staging | `langfuse`, `security` | `staging` | Off | Required |
| Production | `main` | `production` | Off | Required |

---

## 5. Integration Points

| Integration | Protocol | Direction | Purpose |
|-------------|----------|-----------|---------|
| Frontend → Backend | HTTPS REST | Outbound | Agent invocation, session management |
| Backend → Gemini API | HTTPS gRPC-over-REST | Outbound | LLM inference |
| Backend → Langfuse | HTTPS | Outbound | Trace submission, prompt versioning |
| GitHub Actions → GCP | WIF / SA JSON key | Outbound | Docker push, Cloud Run deploy |
| LLM Guard (in-process) | Python library | Internal | Prompt-injection scanning |

---

## 6. Data Flow Across Components

### 6.1 Resume Analysis Request

```
User (browser)
  │  POST /api/v1/chat
  │  { intent, resumeData/resumeFile, jobDescription, messageHistory }
  ▼
FastAPI endpoint (chat.py)
  │  validate schema (Pydantic v2)
  │  bind SessionContext(session_id, user_id)
  ▼
OrchestrationAgent.orchestrate()
  │  parse intent → select agent sequence
  │  normalise resume (resumeData or extract from PDF)
  ▼
LangGraph StateGraph
  │  _run_agent() per agent in sequence
  │  ┌──────────────────────────────────────┐
  │  │  LLMGuardScanner.scan_input()        │ ← blocks prompt injection
  │  │  GeminiService.generate_response()   │ ← LLM call
  │  │  LLMGuardScanner.scan_output()       │ ← flags sensitive output
  │  │  OutputSanitizer.sanitize()          │ ← strips PII / harmful content
  │  │  SharpGovernanceService.audit()      │ ← adds confidence & hallucination metadata
  │  └──────────────────────────────────────┘
  │  append to decision_trace, shared_memory
  ▼
ChatApiResponse → JSON → Frontend
  │  display analysis, HITL approval gates
```

### 6.2 State Schema (SessionContext)

```
SessionContext
├── session_id: str
├── user_id: Optional[str]
├── resume_data: Optional[str]
├── job_description: Optional[str]
├── shared_memory: Dict[str, Any]     # accumulates across agents
├── decision_trace: List[str]         # breadcrumb audit trail
└── conversation_history: List[AgentResponse]
```

---

## 7. Architectural Style Justification

### 7.1 Multi-Agent with LangGraph

**Choice:** LangGraph `StateGraph` instead of simple sequential function calls.

**Justification:**
- Enables stateful, recoverable workflows with checkpointing.
- Conditional edge routing (`continue` / `end`) allows future branching (parallel agents, retry loops).
- Consistent with LangChain ecosystem tooling and Langfuse native integration.

### 7.2 FastAPI + Pydantic v2

**Choice:** FastAPI over Flask/Django.

**Justification:**
- Async-first: non-blocking I/O for concurrent agent calls.
- Automatic OpenAPI docs with schema validation reduces integration bugs.
- Pydantic v2 provides strict type safety and fast serialisation, critical for agent input/output contracts.

### 7.3 Microservice Deployment (Cloud Run)

**Choice:** Separate frontend and backend services on Cloud Run.

**Justification:**
- Independent scaling: backend scales on compute-heavy LLM workloads; frontend scales on request volume.
- Stateless containers simplify horizontal scaling and zero-downtime deployments.
- No idle costs; Cloud Run scales to zero when unused.

### 7.4 External LLM (Gemini) vs Self-Hosted

**Choice:** Google Gemini API (`gemini-2.5-flash`).

**Justification:**
- No GPU infrastructure overhead.
- SLA-backed latency; meets the ≤5 s analysis requirement.
- `gemini-2.5-flash` balances cost and reasoning quality for resume analysis tasks.

### 7.5 Langfuse for Observability

**Choice:** Langfuse over custom logging or OpenTelemetry alone.

**Justification:**
- Purpose-built for LLM traces: tracks tokens, costs, and prompt versions.
- Session-level aggregation aligns with HITL audit requirements.
- Supports LLM-as-a-judge evaluations for future automated quality gates.
