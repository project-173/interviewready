# InterviewReady (Job Agent System)

A stateful, multi-agent AI system for resume optimization using LangGraph orchestration with integrated feedback loops.

## Overview

InterviewReady is a high-integrity AI system that converts unstructured resumes into optimized, job-aligned documents through a **Diagnostic-Actuation-Audit** pattern. The system uses LangGraph-based orchestration with mathematical justification via SHAP analysis and verification via Natural Language Inference (NLI).

## Architecture

### Core Components

- **LangGraph State Machine**: Persistent orchestration with checkpoint-based recovery
- **Multi-Agent Pipeline**: 7 specialized agents for resume analysis and optimization
- **PostgreSQL + pgvector**: Vector similarity search and structured data storage
- **LangFuse Observability**: End-to-end tracing and monitoring
- **Human-in-the-Loop**: Strategic interrupts for user approval at critical points

### Agent Workflow

1. **ExtractorAgent**: Parses PDFs into structured ResumeSchema
2. **Router**: Determines workflow path and flags stale resumes
3. **ResumeCriticAgent**: Evaluates structural quality and ATS readability
4. **ContentStrengthSkillsReasoningAgent**: Analyzes skills and achievements
5. **JobDescriptionAlignmentAgent**: Semantic matching and role fit assessment
6. **InterviewCoachFeedbackAgent**: Role-specific interview simulation
7. **Validator**: NLI-based integrity checking and hallucination detection

## Quick Start

### Prerequisites

- Java 17 (for Backend)
- Node.js 20+ (for Frontend)
- Docker & Docker Compose (for Containerization)
- Google Cloud SDK (for GCP Deployment)

### Local Development
### Development Commands
| Task | Command |
|------|---------|
| Backend Setup | `cd backend && uv sync` |
| Frontend Setup | `cd frontend && npm install` |
| Run Backend | `cd backend && uv run fastapi dev` |
| Run Frontend | `cd frontend && npm run dev` |
| Backend Tests | `cd backend && uv run python -m pytest` |
| Frontend Tests | `cd frontend && npm run test` |
| Code Linting | `cd backend && ruff check .` |
| Code Formatting | `cd backend && ruff format .` |
| Type Checking | `cd backend && mypy .` |

### Containerization

#### Run with Docker Compose
You can run the entire stack locally using Docker:

```bash
docker-compose up --build
```
- Frontend: `http://localhost:80`
- Backend: `http://localhost:8080`

### Deployment to GCP

This project is configured for deployment to **GCP Cloud Run** via GitHub Actions.

#### Setup Requirements:
1. **Artifact Registry**: Create a repository named `interviewready-repo` in `us-central1`.
2. **GitHub Secrets**: Add `GCP_SA_KEY` (Service Account JSON) to your repository.
3. **Environment Variables**: Update `PROJECT_ID` in `.github/workflows/gcp-deploy.yaml` if necessary.

The pipeline will automatically build and deploy both services to Cloud Run on every push to the `main` branch.


## Directory Structure

```
/backend/
├── agents/           # Agent implementations
├── core/            # Shared domain logic, schemas
├── storage/         # Database models, migrations
├── utils/           # Utilities (NLI, embeddings, etc.)
├── api/             # FastAPI endpoints
├── tests/           # Unit, integration, e2e tests
└── pipeline.py      # LangGraph orchestration entry point

/frontend/
├── src/
│   ├── components/  # React components
│   ├── services/    # API clients
│   ├── store/       # State management
│   └── types/       # TypeScript definitions
└── package.json
```

## Technical Stack

- **Orchestration**: LangGraph (stateful graph cycles)
- **Parsing**: LlamaParse (Markdown-centric PDF parsing)
- **Database**: PostgreSQL + pgvector for vector similarity
- **LLMs**: GPT-4o or Claude 3.5 Sonnet
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **Explainability**: SHAP KernelExplainer
- **Validation**: DeBERTa-v3-large-mnli (NLI)
- **Schema**: Pydantic V2
- **API**: FastAPI
- **Frontend**: React + TypeScript

## Key Features

### Persistent State Management
- Short-term checkpoints for session recovery
- Long-term structured resume storage
- Vector embeddings for semantic search
- Immutable state updates with full audit trails

### Mathematical Justification
- SHAP-based feature importance analysis
- Deterministic scoring formulas
- Composite alignment scores with version-controlled weights
- Regression testing with "Golden Set" resume/JD pairs

### Safety & Integrity
- NLI-based hallucination detection
- PII masking and encryption
- Complete agent decision logging
- Human-in-the-loop validation at critical points

## Performance Requirements

- Resume analysis: <5s
- Optimization suggestions: <10s
- Database queries: <100ms
- State recovery: <2s
- Concurrent users: 100+

## Testing Strategy

- **Unit Tests**: Agent logic, deterministic scoring
- **Integration Tests**: State flow, database operations
- **Golden Set E2E**: Regression testing with predefined resume/JD pairs
- **CI Pipeline**: Lint, format, type check, automated testing