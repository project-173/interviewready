# System Architecture Document — InterviewReady

## 1. Executive Summary

InterviewReady is a **multi-agent AI system** that helps candidates optimise their resumes and prepare for interviews. It exposes a stateful RESTful API backed by four specialised AI agents orchestrated via LangGraph, with a React single-page application as the front end. A Gemini Live WebSocket endpoint enables real-time voice-based mock interviews. Agent outputs are automatically evaluated by an **LLM-as-a-judge** module, and all decisions are traced through Langfuse. A multi-layered governance stack (SHARP, LLM Guard, OutputSanitizer) enforces confidence thresholds, hallucination checks, and bias controls before any response reaches the user.

---

## 2. Logical Architecture

### 2.1 Layered View

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                       │
│  React 18 + TypeScript  ·  Tailwind CSS  ·  Vite            │
│  Workflow steps UI · HITL approval · Voice interview relay   │
└──────────────────────────────┬──────────────────────────────┘
                               │  HTTPS REST / WebSocket
┌──────────────────────────────▼──────────────────────────────┐
│                       API Layer                              │
│  FastAPI · Pydantic v2 · CORS · Rate Limiter (slowapi)       │
│  POST /api/v1/chat          – multi-intent agent dispatch    │
│  GET  /api/v1/agents        – agent registry & prompts       │
│  GET  /api/v1/sessions      – session management             │
│  GET  /api/v1/interview/token  – GeminiLive session config   │
│  WS   /api/v1/interview/live   – real-time voice relay       │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                  Orchestration Layer                         │
│  LangGraph (StateGraph)  ·  OrchestrationAgent              │
│  Intent routing · Resume normalisation · Context propagation │
└──────┬─────────────┬─────────────┬──────────────┬───────────┘
       │             │             │              │
┌──────▼──┐  ┌───────▼──┐  ┌──────▼─────┐  ┌────▼────────────┐
│ Resume  │  │ Content  │  │    Job     │  │  Interview      │
│ Critic  │  │ Strength │  │ Alignment  │  │  Coach          │
│ Agent   │  │  Agent   │  │  Agent     │  │  Agent          │
└──────┬──┘  └───────┬──┘  └──────┬─────┘  └────┬────────────┘
       └─────────────┴─────────────┴──────────────┘
                               │  Gemini API calls (text)
┌──────────────────────────────▼──────────────────────────────┐
│                   AI Model Layer                             │
│  GeminiService / GeminiLiveService  ·  MockGeminiService    │
│  google-generativeai (gemini-2.5-flash / gemini-3.1-flash-  │
│    live-preview for voice)                                   │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│               Governance & Security Layer                    │
│  SharpGovernanceService · LLMGuardScanner                   │
│  OutputSanitizer · ConfidenceThreshold · HallucinationCheck │
│  InterviewCoachAgent bias / injection / sensitive checks    │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│           LLM-as-a-Judge Evaluation Layer                    │
│  LLmasJudgeEvaluator  ·  eval_rubrics.py (per-agent)        │
│  Scores: quality, accuracy, helpfulness (0–1 each)          │
│  Attached to Langfuse traces via score API                  │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│              Observability & Persistence Layer               │
│  Langfuse (tracing, cost, prompts, judge scores)            │
│  In-memory SessionStore · Structured JSON logging (stdout)  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **React SPA** | Upload resumes, submit job descriptions, approve/reject HITL suggestions, display interview coaching UI, relay WebSocket audio for voice interviews |
| **FastAPI** | Request routing, schema validation, CORS, request-size enforcement, rate limiting, session context binding |
| **Rate Limiter** (`core/limiter.py`) | `slowapi` with `DEFAULT_RATE_LIMIT` (default 20 req/min) to prevent API abuse |
| **OrchestrationAgent** | Translate intent to agent sequence, run LangGraph workflow, propagate `SessionContext` state |
| **ExtractorAgent** | PDF → structured `Resume` via LLM; confidence scoring with `_confidence.overall` / `low_confidence_fields`; HITL review gate on low-confidence extractions |
| **ResumeCriticAgent** | ATS issue list (`ResumeCriticReport.issues`) with location, type, severity, description; summary and score |
| **ContentStrengthAgent** | Faithful rephrasing suggestions (`ContentStrengthReport`) with JSON-path locations, evidence strength, suggestion type; faithfulness-first design |
| **JobAlignmentAgent** | Resume–JD semantic matching producing `AlignmentReport` (skillsMatch, missingSkills, experienceMatch, summary) using JSON-path references into the resume |
| **InterviewCoachAgent** | Two-phase: evaluator sub-prompt scores candidate answers → coach sub-prompt generates next question; 5-question progression with `can_proceed` gate; bias/injection/sensitive-content detection |
| **GeminiLive** | WebSocket relay class connecting browser audio streams to Gemini Live API for real-time voice mock interviews (`gemini-3.1-flash-live-preview`) |
| **LLmasJudgeEvaluator** | LLM-as-a-judge evaluator that independently scores agent outputs on quality, accuracy, and helpfulness; submits scores to Langfuse |
| **GeminiService / GeminiLiveService** | Gemini API wrappers; `GeminiLiveService` supports audio modality |
| **SharpGovernanceService** | Hallucination risk scoring, confidence threshold enforcement, audit metadata; InterviewCoachAgent-specific checks (bias, injection, sensitive content) |
| **LLMGuardScanner** | `PromptInjection` scanner (input), `NoRefusal` + `Sensitive` scanners (output) |
| **Langfuse** | Distributed tracing per session, cost tracking, prompt versioning, LLM judge score ingestion |

---

## 3. Physical / Infrastructure Architecture

### 3.1 Deployment Topology (Production — GCP)

```
Internet
   │
   ├── HTTPS ──► Cloud Run: interviewready-frontend (React)
   │   WSS  ─────────────────────────────────────────────────────┐
   │                             │ HTTPS REST                    │
   │                             ▼                               │
   └──────────────────► Cloud Run: interviewready-backend (FastAPI)
                                  │                              │
                         ┌────────┼──────────┐                   │
                         │        │          │                   │
                    Gemini API  Gemini   Langfuse Cloud          │
                  (text LLM)   Live API  (cloud.langfuse.com)   │
                 (google.com) (audio)                            │
                                  ▲                              │
                                  └── WebSocket relay ──────────┘
```

### 3.2 Infrastructure Components

| Resource | Type | Region | Purpose |
|----------|------|--------|---------|
| `interviewready-backend` | Cloud Run service | asia-southeast1 | FastAPI application, 4 GiB RAM |
| `interviewready-frontend` | Cloud Run service | asia-southeast1 | Nginx-served React SPA |
| `interviewready-repo` | Artifact Registry | asia-southeast1 | Docker image storage |
| `github-deployer` | GCP Service Account | — | CI/CD deployment identity |
| Gemini API (text) | External managed service | google.com | LLM inference for all text agents |
| Gemini Live API | External managed service | google.com | Real-time audio/voice interview |
| Langfuse Cloud | External managed service | cloud.langfuse.com | Observability, eval scores |

### 3.3 Containerisation

- **Backend** (`backend/Dockerfile`): Python image with `uv` for fast dependency resolution; exposes port 8080; includes `slowapi` for rate limiting.
- **Frontend** (`frontend/Dockerfile`): Multi-stage build (Node.js build → Nginx serve); exposes port 80.
- Both images are AMD64-targeted for Cloud Run compatibility.

---

## 4. Service Deployment Strategy

### 4.1 CI/CD Pipeline (GitHub Actions — `.github/workflows/deploy.yml`)

```
Push to main / CICD / langfuse / security / sit
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

### 4.2 Eval Runner Pipeline (`.github/workflows/eval-runner.yml`)

A separate **manual-dispatch** workflow runs LLM-as-a-judge evaluations against Langfuse datasets:

```
workflow_dispatch (agent, dataset, max_cases, run_name, trace_id)
          │
          ▼
  Install Python dependencies (uv sync)
          │
          ▼
  Run evals/run_evals.py
    ├─ Load eval datasets (evals/datasets/)
    ├─ Run agent with real Gemini API
    ├─ Score output with LLmasJudgeEvaluator
    └─ Submit scores to Langfuse
          │
          ▼
  Post results as PR comment / issue
```

### 4.3 Environment Strategy

| Environment | Branch | `APP_ENV` | Mock Agents | Langfuse | Eval Tests |
|-------------|--------|-----------|-------------|---------|-----------|
| Local | any | `local` | Optional via `.env` | Optional | `SKIP_EVAL_TESTS=true` |
| Staging | `langfuse`, `security`, `sit` | `staging` | Off | Required | `SKIP_EVAL_TESTS=true` |
| Production | `main` | `production` | Off | Required | Manual eval runner |

---

## 5. Integration Points

| Integration | Protocol | Direction | Purpose |
|-------------|----------|-----------|---------|
| Frontend → Backend (REST) | HTTPS | Outbound | Agent invocation, session management |
| Frontend ↔ Backend (WebSocket) | WSS | Bidirectional | Voice interview audio relay |
| Backend → Gemini API (text) | HTTPS | Outbound | LLM inference for analysis agents |
| Backend → Gemini Live API | WSS/HTTPS | Outbound | Real-time audio for voice interviews |
| Backend → Langfuse | HTTPS | Outbound | Trace submission, judge score ingestion |
| GitHub Actions → GCP | WIF / SA JSON key | Outbound | Docker push, Cloud Run deploy |
| GitHub Actions → Langfuse | HTTPS | Outbound | Eval score submission (`eval-runner.yml`) |
| LLM Guard (in-process) | Python library | Internal | Prompt-injection and sensitive-content scanning |
| slowapi Rate Limiter (in-process) | WSGI middleware | Internal | Request rate enforcement |

---

## 6. Data Flow Across Components

### 6.1 Resume Analysis Request (REST)

```
User (browser)
  │  POST /api/v1/chat
  │  { intent, resumeData/resumeFile, jobDescription, messageHistory }
  ▼
FastAPI endpoint (chat.py)
  │  rate-limit check (slowapi 20/min)
  │  validate schema (Pydantic v2)
  │  bind SessionContext(session_id, user_id)
  ▼
OrchestrationAgent.orchestrate()
  │  parse intent → select agent sequence
  │  normalise resume (resumeData or extract from PDF via ExtractorAgent)
  │    └─ if needs_review → return NormalizationFailure to user
  ▼
LangGraph StateGraph (_run_agent loop)
  │  ┌──────────────────────────────────────────────────┐
  │  │  LLMGuardScanner.scan_input()                    │ ← blocks injection
  │  │  GeminiService.generate_response()               │ ← LLM call
  │  │  LLMGuardScanner.scan_output()                   │ ← flags sensitive
  │  │  OutputSanitizer.sanitize()                      │ ← strips PII
  │  │  SharpGovernanceService.audit()                  │ ← governance metadata
  │  └──────────────────────────────────────────────────┘
  │  append to decision_trace, shared_memory
  ▼
ChatApiResponse
  │  { agent, payload, confidence_score, needs_review, low_confidence_fields }
  ▼
Frontend — display analysis, HITL approval gates
```

### 6.2 Voice Interview Request (WebSocket)

```
User (browser)
  │  WSS /api/v1/interview/live?sessionId=abc
  ▼
FastAPI WebSocket endpoint (interview.py)
  │  GET /api/v1/interview/token → returns { api_key, model, system_instruction }
  │    └─ system_instruction includes resume_data + job_description from SessionContext
  │  Accept WebSocket
  ▼
GeminiLive.start_session()
  │  audio_input_queue, text_input_queue → Gemini Live API (gemini-3.1-flash-live-preview)
  │  audio_output_callback → browser
  │  Bidirectional: browser audio ↔ Gemini Live ↔ browser audio response
  ▼
Frontend — plays AI interviewer audio, captures candidate microphone
```

### 6.3 LLM-as-a-Judge Evaluation Flow

```
evals/run_evals.py (CI or manual)
  │  load EvalCase from evals/datasets/
  ▼
Agent.process(input_data, context)  ← real Gemini call
  │  response.content
  ▼
LLmasJudgeEvaluator.evaluate()
  │  build_judge_prompt(agent_name, input, output, expected)
  │  GeminiService → judge LLM call (temperature=0.0)
  │  parse JudgeEvaluation { quality_score, accuracy_score, helpfulness_score }
  ▼
langfuse.score()  ← attach scores to parent trace
  │  quality / accuracy / helpfulness scores visible in Langfuse dashboard
```

### 6.4 Updated State Schema (SessionContext)

```
SessionContext
├── session_id: str
├── user_id: Optional[str]
├── resume_data: Optional[str | dict]     # set by ExtractorAgent or resumeData
├── job_description: Optional[str]
├── shared_memory: Dict[str, Any]         # accumulates across agents
├── decision_trace: List[str]             # breadcrumb audit trail
└── conversation_history: List[AgentResponse]
```

### 6.5 Updated AgentResponse Schema

```
AgentResponse
├── agent_name: Optional[str]
├── content: Optional[str]                # JSON-serialised structured result
├── reasoning: Optional[str]             # human-readable explanation
├── confidence_score: Optional[float]
├── needs_review: Optional[bool]         # NEW: flags low-confidence extractions
├── low_confidence_fields: List[str]     # NEW: fields that need human review
├── decision_trace: List[str]
└── sharp_metadata: Dict[str, Any]       # governance audit data
```

---

## 7. Updated Output Schemas

| Agent | Schema Class | Key Fields |
|-------|-------------|-----------|
| **ResumeCriticAgent** | `ResumeCriticReport` | `issues[]{location, type, severity, description}`, `summary`, `score` |
| **ContentStrengthAgent** | `ContentStrengthReport` | `suggestions[]{location, original, suggested, evidenceStrength, type}`, `summary`, `score` |
| **JobAlignmentAgent** | `AlignmentReport` | `skillsMatch[]` (JSON paths), `missingSkills[]`, `experienceMatch[]` (JSON paths), `summary` |
| **InterviewCoachAgent** | Inline JSON | `current_question_number`, `total_questions`, `interview_type`, `question`, `keywords`, `tip`, `feedback`, `answer_score`, `can_proceed`, `next_challenge` |
| **ExtractorAgent** | `Resume` + `_confidence` | Full JSON Resume schema + `_confidence.{overall, low_confidence_fields, reasons}` |

---

## 8. Architectural Style Justification

### 8.1 Multi-Agent with LangGraph

**Choice:** LangGraph `StateGraph` instead of simple sequential function calls.

**Justification:**
- Enables stateful, recoverable workflows with checkpointing.
- Conditional edge routing (`continue` / `end`) allows future branching (parallel agents, retry loops).
- Consistent with LangChain ecosystem tooling and Langfuse native integration.

### 8.2 FastAPI + Pydantic v2 + slowapi

**Choice:** FastAPI over Flask/Django; `slowapi` for rate limiting.

**Justification:**
- Async-first: non-blocking I/O for concurrent agent calls and WebSocket handling.
- Automatic OpenAPI docs with schema validation reduces integration bugs.
- Pydantic v2 strict typing enforces agent I/O contracts.
- `slowapi` provides per-IP rate limiting without infrastructure overhead.

### 8.3 Microservice Deployment (Cloud Run)

**Choice:** Separate frontend and backend services on Cloud Run.

**Justification:**
- Independent scaling: backend scales on compute-heavy LLM workloads; frontend scales on request volume.
- Stateless containers simplify horizontal scaling and zero-downtime deployments.
- No idle costs; Cloud Run scales to zero when unused.
- Sufficient memory (4 GiB) for in-memory session store and llm-guard model loading.

### 8.4 Gemini Text + Gemini Live

**Choice:** Google Gemini API (`gemini-2.5-flash`) for text agents; `gemini-3.1-flash-live-preview` for real-time voice.

**Justification:**
- Single vendor simplifies API key management and billing.
- `gemini-2.5-flash` meets the ≤5 s analysis requirement for text agents.
- Gemini Live API provides ultra-low-latency bidirectional audio for realistic voice interviews without managing a separate speech-to-text pipeline.

### 8.5 LLM-as-a-Judge for Quality Assurance

**Choice:** `LLmasJudgeEvaluator` using a separate Gemini call at `temperature=0.0`.

**Justification:**
- Provides automated, scalable quality checks that are independent of the agent under evaluation.
- Temperature=0 maximises consistency of judge scores.
- Langfuse score API enables trend analysis and regression detection across releases.

### 8.6 Langfuse for Observability + Eval Scores

**Choice:** Langfuse over custom logging or OpenTelemetry alone.

**Justification:**
- Purpose-built for LLM traces: tracks tokens, costs, and prompt versions.
- Session-level aggregation aligns with HITL audit requirements.
- Native LLM-as-a-judge score ingestion closes the evaluation feedback loop.
