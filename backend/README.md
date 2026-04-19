# InterviewReady Backend: Python FastAPI Multi-Agent Orchestration Engine

Production-ready Python FastAPI backend with LangGraph-based multi-agent AI orchestration for resume optimization and interview coaching.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Technology Stack](#technology-stack)
3. [Setup & Installation](#setup--installation)
4. [Agent System](#agent-system)
5. [API Documentation](#api-documentation)
6. [Configuration](#configuration)
7. [Security & Governance](#security--governance)
8. [Testing](#testing)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)

---

## 1. Architecture Overview

### Backend Component Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  API LAYER (app/api/v1/)                                        │
│  ├─ POST /chat          (Multi-intent routing)                  │
│  ├─ GET  /agents        (Agent registry)                        │
│  └─ GET  /health        (System status)                         │
│                                                                  │
│  ↓↓↓                                                             │
│                                                                  │
│  ORCHESTRATION LAYER (app/orchestration/)                       │
│  ├─ Intent extraction & classification                          │
│  ├─ Agent dispatcher (LangGraph state machine)                  │
│  └─ Session state management                                    │
│                                                                  │
│  ↓↓↓                                                             │
│                                                                  │
│  AGENT LAYER (app/agents/)                                      │
│  ├─ BaseAgent (mixin: LLM Guard, sanitization, logging)        │
│  ├─ ResumeCriticAgent                                           │
│  ├─ ContentStrengthAgent                                        │
│  ├─ JobAlignmentAgent                                           │
│  ├─ InterviewCoachAgent (stateful)                              │
│  └─ GeminiService (LLM API wrapper)                             │
│                                                                  │
│  ↓↓↓                                                             │
│                                                                  │
│  GOVERNANCE LAYER (app/governance/)                             │
│  ├─ SharpGovernanceService (IMDA alignment)                     │
│  ├─ Hallucination detection                                     │
│  ├─ Bias flag detection                                         │
│  └─ Confidence threshold validation                             │
│                                                                  │
│  ↓↓↓                                                             │
│                                                                  │
│  SECURITY LAYER (app/security/)                                 │
│  ├─ LLM Guard scanner (prompt injection defense)               │
│  └─ Output sanitizer (PII, hallucination detection)            │
│                                                                  │
│  DATA & OBSERVABILITY                                           │
│  ├─ Models (Pydantic V2 schemas)                               │
│  ├─ Database (SQLAlchemy async ORM)                            │
│  ├─ Structured logging (JSON)                                  │
│  └─ Langfuse tracing integration                               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
HTTP Request
  ↓
FastAPI Endpoint (POST /api/v1/chat)
  • Session validation
  • CORS handling
  • Request body parsing (Pydantic)
  ↓
Orchestration Engine
  • Intent extraction
  • Resume normalization
  • Route to appropriate agent(s)
  ↓
Selected Agent Processing
  1. Input LLM Guard scan (prompt injection detection)
  2. PII redaction if sensitive
  3. Construct system prompt + user input
  4. Call Gemini API (with fallback to mock)
  5. Parse and validate output (schema-constrained JSON)
  6. Output sanitization & logging
  ↓
Governance Audit
  • Hallucination risk assessment
  • Confidence threshold validation
  • Bias flag detection
  • Append governance metadata
  ↓
Langfuse Tracing & Logging
  • Submit trace to Langfuse (non-blocking)
  • Write structured JSON log entry
  • Update session state
  ↓
Response Aggregation & Return
  • Package response with decision_trace
  • Include confidence scores & reasoning
  • Return JSON to client
```

---

## 2. Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Web Framework** | FastAPI | 0.100+ | High-performance async REST API |
| **ASGI Server** | Uvicorn | 0.24+ | ASGI server implementation |
| **Python** | 3.11+ | Latest | Language runtime |
| **LLM Orchestration** | LangGraph | Latest | Stateful multi-agent workflows |
| **LLM Integration** | LangChain | Latest | LLM chain utilities |
| **Data Validation** | Pydantic V2 | 2.x | Type-safe schemas & validation |
| **Database ORM** | SQLAlchemy | 2.0+ | Async-first database abstraction |
| **Dependency Injection** | FastAPI (builtin) | — | Injection container |
| **Async Runtime** | asyncio | Python stdlib | Async/await support |
| **Configuration** | python-dotenv | Latest | Environment variable loading |
| **Logging** | Python logging + JSON | Stdlib | Structured logging |
| **Security Scanning** | LLM Guard | Latest | Prompt injection & output safety |
| **Observability** | Langfuse | Cloud/OSS | LLM tracing & evaluation platform |
| **Testing** | pytest | 7.4+ | Unit & integration testing |
| **Type Checking** | mypy | Latest | Static type analysis |

---

## 3. Setup & Installation

### Prerequisites

- **Python 3.11+** - Install from [python.org](https://www.python.org/)
- **uv package manager** - Install via `pip install uv` or see [astral.sh/uv](https://astral.sh/uv/)
- **Google Gemini API Key** - Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
- **Git** - For version control
- **Docker** (Optional) - For containerized development

### Installation Steps

**1. Clone Repository & Install Dependencies**
```bash
cd backend
uv sync
```

**2. Create Environment File**
```bash
cp .env.example .env
```

**3. Configure Environment Variables**
Edit `.env` with your credentials:
```bash
# Required
GEMINI_API_KEY=<your-google-gemini-api-key>
APP_ENV=local  # local, staging, production

# Optional: Langfuse (for distributed tracing)
LANGFUSE_PUBLIC_KEY=<your-langfuse-public-key>
LANGFUSE_SECRET_KEY=<your-langfuse-secret-key>
LANGFUSE_BASE_URL=https://cloud.langfuse.com

# Optional: Agent Configuration
MOCK_RESUME_CRITIC_AGENT=false
MOCK_CONTENT_STRENGTH_AGENT=false
MOCK_JOB_ALIGNMENT_AGENT=false
MOCK_INTERVIEW_COACH_AGENT=false

# Optional: API Configuration
API_RATE_LIMIT=100  # requests per minute
API_TIMEOUT=30      # seconds
```

**4. Run the Application**
```bash
uv run python -m app.main
```

The application will start at `http://localhost:8000`

**5. Access API Documentation**
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 4. Agent System

### Agent Overview

Each agent is specialized for a specific resume/interview analysis task:

| Agent | Input | Output | Use Case | Reasoning |
|-------|-------|--------|----------|-----------|
| **ResumeCriticAgent** | Resume text/PDF | Markdown critique | Identify ATS issues, formatting problems | Structural analysis with scoring |
| **ContentStrengthAgent** | Resume text | JSON with skills/achievements | Evaluate content impact and evidence | Evidence-strength scoring with confidence |
| **JobAlignmentAgent** | Resume + Job Description | JSON alignment report | Match skills to job requirements | Semantic similarity & gap analysis |
| **InterviewCoachAgent** | Resume + JD + History | JSON questions/feedback | Role-specific interview practice | Schema-constrained multi-turn coaching |

### BaseAgent Mixin (Security & Observability)

All agents inherit from `BaseAgent` which provides:

```python
class BaseAgent(ABC, BaseAgentProtocol):
    """Abstract base agent with security & observability mixins."""
    
    def __init__(self, gemini_service: GeminiService, system_prompt: str, name: str):
        self.gemini_service = gemini_service        # LLM API wrapper
        self.system_prompt = system_prompt          # Agent-specific prompt
        self.name = name                            # Agent identifier
    
    def process(self, input_data: AgentInput, context: SessionContext) -> AgentResponse:
        """Process input with security checks & governance."""
        # 1. Input validation & schema enforcement
        # 2. LLM Guard scan (prompt injection defense)
        # 3. PII redaction if needed
        # 4. Call Gemini with retry logic
        # 5. Output sanitization & validation
        # 6. Structured logging via Langfuse
        # 7. Return AgentResponse with decision_trace
        pass
```

**Built-in Security Controls:**
- ✅ **Input Security:** LLM Guard scanning for prompt injection patterns
- ✅ **Output Safety:** Sanitization (hallucination detection, PII removal)
- ✅ **Error Handling:** Retry logic, mock response fallback, grace ful degradation
- ✅ **Tracing:** Langfuse integration, decision_trace field, execution timing
- ✅ **Governance:** SHARP audit applied post-agent-response

### Agent Configuration

Edit agent system prompts in `app/agents/`:

```python
# example: ResumeCriticAgent
SYSTEM_PROMPT = """
You are an expert resume reviewer...
Evaluate the resume structure, ATS compatibility, and content quality.
Respond with a STRUCTURED JSON OBJECT containing:
{
  "score": <0-100>,
  "sections": {...},
  "issues": [...],
  "suggestions": [...]
}
"""
```

### Mock Mode

For development without API calls, enable mock mode in `.env`:

```bash
MOCK_RESUME_CRITIC_AGENT=true
MOCK_CONTENT_STRENGTH_AGENT=true
MOCK_JOB_ALIGNMENT_AGENT=true
MOCK_INTERVIEW_COACH_AGENT=true
```

Mock responses defined in `app/mock_responses.json`:
```json
{
  "ResumeCriticAgent": "Mock response content...",
  "ContentStrengthAgent": "{\"skills\": [...]}",
  ...
}
```

---

## 5. API Documentation

### Endpoints

#### POST `/api/v1/chat`

Main orchestration endpoint for all agent interactions.

**Request:**
```json
{
  "intent": "RESUME_CRITIC|CONTENT_STRENGTH|ALIGNMENT|INTERVIEW_COACH",
  "resumeData": {
    "contact": "John Doe...",
    "work": [...],
    "skills": [...]
  },
  "resumeFile": {
    "data": "<base64-pdf>",
    "fileType": "pdf"
  },
  "jobDescription": "Senior Software Engineer...",
  "messageHistory": [
    {"role": "user", "text": "..."},
    {"role": "assistant", "text": "..."}
  ],
  "audioData": null
}
```

**Response:**
```json
{
  "agent": "ResumeCriticAgent",
  "payload": "...",
  "confidence_score": 0.92,
  "needs_review": false,
  "low_confidence_fields": [],
  "decision_trace": [
    "Orchestrator: Routed to ResumeCriticAgent based on intent",
    "ResumeCriticAgent: Evaluated 5 resume sections",
    "Governance: Confidence 0.92 exceeds threshold"
  ]
}
```

**Response Fields:**
- `agent` - Which agent processed the request
- `payload` - Agent response (format varies by agent type)
- `confidence_score` - (0.0-1.0) Decision certainty
- `needs_review` - Boolean flag for human review escalation
- `low_confidence_fields` - Array of fields below confidence threshold
- `decision_trace` - Array of reasoning steps for auditability

#### GET `/api/v1/agents`

List available agents and their current system prompts.

**Response:**
```json
{
  "agents": [
    {
      "name": "ResumeCriticAgent",
      "intent": "RESUME_CRITIC",
      "description": "Analyzes resume structure and ATS readability",
      "system_prompt": "..."
    },
    ...
  ]
}
```

#### GET `/api/v1/health`

System health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-03-31T12:00:00Z",
  "services": {
    "gemini": "operational",
    "langfuse": "operational",
    "database": "operational"
  },
  "version": "1.0.0"
}
```

### Error Handling

All endpoints follow consistent error format:

```json
{
  "detail": "Error description",
  "error_code": "INVALID_REQUEST|API_ERROR|GOVERNANCE_REJECTION",
  "timestamp": "2024-03-31T12:00:00Z",
  "request_id": "<session-id>"
}
```

**Common Status Codes:**
- `200 OK` - Successful request
- `400 Bad Request` - Invalid input (schema validation failed)
- `401 Unauthorized` - Missing/invalid session ID
- `422 Unprocessable Entity` - Governance rejection (low confidence, bias flags)
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - API or service failure (with mock fallback)

---

## 6. Configuration

### Environment Variables

**Core Configuration:**
```bash
# API
APP_ENV=local|staging|production      # Execution environment
API_RATE_LIMIT=100                    # Requests per minute
API_TIMEOUT=30                        # Request timeout (seconds)

# LLM API (Required)
GEMINI_API_KEY=sk-...                 # Google Gemini API key

# Observability (Optional)
LANGFUSE_PUBLIC_KEY=pk-...            # Langfuse public key
LANGFUSE_SECRET_KEY=sk-...            # Langfuse secret key
LANGFUSE_BASE_URL=https://cloud.langfuse.com  # Langfuse endpoint

# Agent Mock Mode (Optional)
MOCK_RESUME_CRITIC_AGENT=false        # Use mock responses instead of API
MOCK_CONTENT_STRENGTH_AGENT=false
MOCK_JOB_ALIGNMENT_AGENT=false
MOCK_INTERVIEW_COACH_AGENT=false

# Logging
LOG_LEVEL=INFO|DEBUG|WARNING|ERROR    # Application log level
```

### Configuration File

Edit `app/core/config.py` for programmatic configuration:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_ENV: str = "local"
    GEMINI_API_KEY: str = ""
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    API_RATE_LIMIT: int = 100
    # ... more settings
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

---

## 7. Security & Governance

### Input Security

**LLM Guard Scanning** (all agent inputs):
```python
# Blocks prompt injection attempts
from app.security.llm_guard_scanner import get_llm_guard_scanner

scanner = get_llm_guard_scanner()
result = scanner.scan_prompt(user_input)
if result.unsafe:
    # Log security event and reject request
    raise SecurityViolationError(result.violation_types)
```

**Prompt Injection Patterns Detected:**
- "ignore previous instructions"
- "reveal system prompt"
- "act as [jailbreak attempt]"
- Markup tags (`</system>`, `</assistant>`)
- Jailbreak directives

### Output Security

**PII Redaction:**
```python
# InterviewCoachAgent automatically redacts:
SENSITIVE_PATTERNS = {
    "email": r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    "phone": r"...",  # Phone number regex
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b"
}

# Example: "john@example.com" → "[EMAIL_REDACTED]"
```

**Output Sanitization:**
```python
from app.utils.output_sanitizer import get_output_sanitizer

sanitizer = get_output_sanitizer()
safe_output = sanitizer.sanitize(agent_response)
```

### Governance & Bias Mitigation

**SHARP Governance Service:**
```python
from app.governance.sharp_governance_service import SharpGovernanceService

service = SharpGovernanceService()
audit = service.audit_agent_response(
    agent_response=response,
    user_input=user_input,
    context=session_context
)

# Returns:
audit.hallucination_risk_score      # 0.0-1.0
audit.bias_flags                    # ["age_bias", "gender_bias"]
audit.confidence_is_valid           # Boolean
audit.requires_human_review         # Boolean
audit.governance_metadata           # Dict with details
```

**Bias Pattern Detection:**
```python
BIAS_PATTERNS = {
    "age": r"\b(young|recent graduate|digital native)\b",
    "gender": r"\b(he|she|male|female)\b",
    "nationality": r"\b(native english|citizens only)\b"
}
```

**Confidence Thresholds:**
- Minimum confidence for auto-approval: 0.3 (30%)
- Confidence < threshold triggers human review flag
- Editorial note: Thresholds configurable per agent

### Langfuse Integration

**Automatic Tracing:**
```python
from langfuse import Langfuse, observe, propagate_attributes

langfuse = Langfuse()

@observe(name="agent_processing")
def process_with_tracing(input_data, context):
    with propagate_attributes(session_id=context.session_id):
        # All nested spans inherit session context
        response = agent.process(input_data, context)
    return response
```

**Trace Structure in Langfuse Dashboard:**
```
chat_api_request [session_id=abc123]
  ├─ orchestration_agent_dispatch
  │  └─ ResumeCriticAgent_process
  │     ├─ llm_guard_scan (input security)
  │     ├─ call_gemini (LLM inference)
  │     └─ output_sanitization
  ├─ governance_audit
  │  ├─ hallucination_assessment
  │  ├─ bias_detection
  │  └─ confidence_validation
  └─ response_logging
```

---

## 8. Testing

### Running Tests

**Unit Tests:**
```bash
# Run all tests
uv run pytest backend/tests/ -v

# Run specific test file
uv run pytest backend/tests/test_agents.py -v

# Run with coverage
uv run pytest backend/tests/ --cov=app --cov-report=html
```

**Security Tests:**
```bash
# Test prompt injection defense
uv run pytest backend/tests/test_interview_coach.py::test_prompt_injection_defense -v

# Test PII redaction
uv run pytest backend/tests/test_interview_coach.py::test_pii_redaction -v

# Test bias pattern detection
uv run pytest backend/tests/test_interview_coach.py::test_bias_pattern_detection -v
```

**Integration Tests:**
```bash
# Test API endpoints
uv run pytest backend/tests/test_api_endpoints.py -v

# Test multi-turn interview flow
uv run pytest backend/tests/test_interview_coach.py::test_five_question_progression -v
```

### Test Files

| File | Purpose | Test Count |
|------|---------|-----------|
| `test_agents.py` | Agent logic & response generation | 12 |
| `test_orchestration_governance.py` | Orchestration routing & governance audits | 8 |
| `test_api_endpoints.py` | API endpoint request/response handling | 6 |
| `test_interview_coach.py` | Multi-turn interview flow & security | 10 |
| `test_agent_structural_checks.py` | Schema validation & JSON structure | 4 |
| `test_agent_evals.py` | Agent evaluations on Langfuse datasets | 2 |

**Total Test Count:** 42 tests, 100% automated in CI pipeline

### Interactive Testing

**Using Swagger UI** (Recommended):
1. Start backend: `uv run python -m app.main`
2. Open: http://localhost:8000/docs
3. Click "Try it out" on `/api/v1/chat`
4. Enter request JSON, click "Execute"

**Using curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "RESUME_CRITIC",
    "resumeData": {"contact": "John Doe", ...}
  }'
```

---

## 9. Deployment

### Local Development

**Docker Compose:**
```bash
docker-compose up backend
# Backend available at http://localhost:8000
# MockGeminiService active by default
```

### Cloud Deployment

**Google Cloud Run:**
```bash
# Set up GCP project (one-time)
gcloud projects create interviewready-backend

# Deploy via GitHub Actions
git push origin main
# Automatic deployment triggered (see .github/workflows/deploy.yml)

# Manual deployment
gcloud run deploy interviewready-backend \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated
```

**Environment Setup (GCP Secret Manager):**
```bash
gcloud secrets create GEMINI_API_KEY --replication-policy="automatic"
gcloud secrets versions add GEMINI_API_KEY --data-file=<(echo $GEMINI_API_KEY)
```

See **[DEPLOYMENT.md](../DEPLOYMENT.md)** for detailed infrastructure setup.

---

## 10. Troubleshooting

### Common Issues

**Issue: "GEMINI_API_KEY not found"**
```bash
# Solution: Check .env file exists and is sourced
cat .env | grep GEMINI_API_KEY
# Should output: GEMINI_API_KEY=sk-xxx...

# If missing:
cp .env.example .env
# Edit .env with your API key
```

**Issue: "ModuleNotFoundError: No module named 'app'"**
```bash
# Solution: Run from backend directory
cd backend
uv run python -m app.main
# NOT: python app/main.py
```

**Issue: "LangGraph import error"**
```bash
# Solution: Update dependencies
uv sync --upgrade
uv run pip install --upgrade langgraph langchain
```

**Issue: "Port 8000 already in use"**
```bash
# Solution: Change port or kill existing process
uv run python -m app.main --port 8001
# OR
lsof -i :8000 | grep -v PID | awk '{print $2}' | xargs kill -9
```

**Issue: "API returns 500 error"**
```bash
# Check logs
uv run python -m app.main 2>&1 | grep ERROR

# Enable debug logging
export LOG_LEVEL=DEBUG
uv run python -m app.main

# Check Langfuse dashboard for trace details
# https://cloud.langfuse.com
```

### Debug Mode

**Enable verbose logging:**
```bash
export LOG_LEVEL=DEBUG
export APP_ENV=local
uv run python -m app.main
```

**Test with mock responses:**
```bash
export MOCK_RESUME_CRITIC_AGENT=true
export MOCK_CONTENT_STRENGTH_AGENT=true
export MOCK_JOB_ALIGNMENT_AGENT=true
export MOCK_INTERVIEW_COACH_AGENT=true
uv run python -m app.main
```

---

## Additional Resources

- **[Main README](../README.md)** — Project overview & architecture
- **[Deployment Guide](../DEPLOYMENT.md)** — Cloud Run, Docker, Kubernetes
- **[Governance Documentation](../GOVERNANCE.md)** — SHARP framework & tracing
- **[Responsible AI Guide](../docs/interview-agent-responsible-ai.md)** — Security & bias mitigation
- **[Langfuse Documentation](https://docs.langfuse.com/)** — Observability platform
- **[FastAPI Documentation](https://fastapi.tiangolo.com/)** — API framework
- **[Pydantic V2 Documentation](https://docs.pydantic.dev/latest/)** — Validation library

---

**Last Updated:** March 2026  
**Version:** 1.0  
**Maintainers:** InterviewReady Development Team

4. **InterviewCoachAgent**
   - Provides role-specific interview preparation
   - Offers coaching based on resume and job alignment
   - Returns markdown-formatted coaching advice

### Agent Response Formats

- **ResumeCriticAgent**: Markdown text critique
- **ContentStrengthAgent**: JSON with `skills`, `achievements`, `suggestions`, `hallucinationRisk`, `summary`
- **JobAlignmentAgent**: JSON with `skillsMatch`, `missingSkills`, `experienceMatch`, `fitScore`, `reasoning`
- **InterviewCoachAgent**: Markdown text coaching feedback

## Project Structure

```
backend/
├── app/
│   ├── agents/              # Agent implementations
│   │   ├── base.py         # Base agent class with Gemini integration
│   │   ├── resume_critic.py
│   │   ├── content_strength.py
│   │   ├── job_alignment.py
│   │   └── interview_coach.py
│   ├── api/                # API endpoints
│   │   └── v1/
│   │       └── endpoints/
│   │           └── chat.py # Main chat endpoint
│   ├── core/               # Configuration and utilities
│   │   ├── config.py       # Application settings
│   │   └── logging.py      # Structured logging configuration
│   ├── models/             # Data models
│   │   ├── agent.py        # Agent response models
│   │   └── session.py      # Session management models
│   ├── orchestration/      # Workflow orchestration
│   │   └── orchestration_agent.py
│   ├── governance/         # SHARP governance framework
│   │   └── sharp_governance_service.py
│   ├── utils/              # Helper functions
│   └── main.py             # FastAPI application entry point
├── tests/                  # Test suite
└── pyproject.toml          # Project configuration
```

## Development Features

### Mock Mode
Enable mock responses for development and testing:
- Set `MOCK_<agent_name>` in environment variables or `config.py`
- Uses predefined responses from `mock_responses.json`
- Allows development without API keys

### Structured Logging
- Complete request flow tracing
- JSON-formatted logs with session tracking
- Performance monitoring and error context
- Configurable log levels and output formats

### Session Management
- Stateful conversations with session persistence
- Automatic session creation and tracking
- Context preservation across multiple requests

## Testing

Run the test suite:
```bash
uv run pytest
```

Mock mode tests:
```bash
uv run python test_mock_mode.py
```
