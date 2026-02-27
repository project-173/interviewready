# InterviewReady Agent Development Guide

## Repository Layout
- `backend/`: Core Python backend with LangGraph orchestration and multi-agent pipeline
  - `app/agents/`: Individual agent implementations (ExtractorAgent, ResumeCriticAgent, etc.)
  - `app/core/`: Shared domain logic, schemas, and data models
  - `app/storage/`: Database models and storage operations
  - `app/utils/`: Utilities for NLI, embeddings, SHAP analysis, and other ML operations
  - `app/api/`: FastAPI endpoints for external communication
  - `app/governance/`: SHAP governance and compliance modules
  - `app/orchestration/`: LangGraph orchestration and workflow management
  - `app/models/`: Pydantic data models and schemas
  - `tests/`: Unit, integration, and end-to-end tests
  - `main.py`: FastAPI application entry point
- `backend/`: Legacy Java backend (being migrated)
- `frontend/`: React TypeScript client for user interface
  - `components/`: React UI components
  - `tests/`: Frontend integration tests using Vitest
  - `backendService.ts`: Main API client service
  - `geminiService.ts`: Legacy service (deprecated)
  - `types.ts`: TypeScript type definitions
- `docs/`: Project documentation (PRD, Status)
- `.agents/`: Agent-specific configuration and metadata

## Development Commands
| Task | Command |
|------|---------|
| Backend Setup | `cd backend && uv sync` |
| Frontend Setup | `cd frontend && npm install` |
| Run Backend | `cd backend && python -m app.main` |
| Run Frontend | `cd frontend && npm run dev` |
| Backend Tests | `cd backend && pytest tests/` |
| Frontend Tests | `cd frontend && npm run test` |
| Code Linting | `cd backend && ruff check .` |
| Code Formatting | `cd backend && ruff format .` |
| Type Checking | `cd backend && mypy .` |

## Agent Development Guidelines

### Agent Implementation Standards
- **State Management**: Use LangGraph's persistent state with checkpoint-based recovery
- **Mathematical Justification**: Implement SHAP-based feature importance analysis for scoring
- **Validation**: All outputs must pass NLI-based integrity checking
- **Logging**: Complete agent decision logging for audit trails
- **Error Handling**: Graceful degradation with clear error messages

### Code Style & Conventions
- **Python**: Follow PEP 8, use Pydantic V2 for schemas, type hints required
- **TypeScript**: Use functional React components, 2-space indentation, single quotes
- **Naming**: Agent files in `PascalCase` (e.g., `ExtractorAgent.py`), functions in `snake_case`
- **Testing**: Each agent requires unit tests and integration tests

### Testing Strategy
- **Backend Tests**: Unit tests, integration tests, and agent coordination tests using pytest
- **Frontend Tests**: Integration tests using Vitest for API connectivity and service testing
- **Unit Tests**: Agent logic, deterministic scoring formulas, component testing
- **Integration Tests**: State flow, database operations, agent coordination, API endpoints
- **Golden Set E2E**: Regression testing with predefined resume/JD pairs
- **Performance Tests**: Resume analysis <5s, optimization <10s, queries <100ms

## Commit Messages and Pull Requests
- Follow the [Chris Beams](http://chris.beams.io/posts/git-commit/) style for commit messages.
- Every PR should address:
  - **What changed?**
  - **Why?**
  - **Breaking changes?**
- Reference relevant issues and include reproduction steps

For detailed project documentation, see `docs/` directory. For migration status, see `MIGRATION-PLAN.md`.
