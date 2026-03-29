# InterviewReady

An intelligent multi-agent AI system for comprehensive resume optimization and interview preparation.

## Overview

InterviewReady transforms your resume into a powerful career tool through specialized AI agents that analyze content, align with job descriptions, and provide interview coaching. The system uses structured orchestration with comprehensive logging and governance to ensure reliable, traceable results.

## Architecture

### Core Components

- **Multi-Agent System**: Specialized agents for resume analysis, job alignment, and interview coaching
- **Orchestration Engine**: Stateful workflow management with session tracking
- **Structured Logging**: Complete request traceability with JSON logging
- **RESTful API**: FastAPI backend with comprehensive endpoint coverage

### Agent Workflow

1. **ResumeCriticAgent**: Evaluates structural quality and ATS readability
2. **ContentStrengthAgent**: Analyzes skills, achievements, and content effectiveness
3. **JobAlignmentAgent**: Semantic matching with job descriptions and role fit assessment
4. **InterviewCoachAgent**: Role-specific interview preparation and coaching

## Directory Structure

```
├── frontend/          # React TypeScript application
├── backend/           # Python FastAPI server
├── docs/              # Project documentation
└── .agents/           # Agent skills and configurations
```

## Getting Started

- [Frontend Setup](frontend/README.md) - React application setup and API integration
- [Backend Setup](backend/README.md) - Python server setup and agent configuration

## Evaluations

The system includes comprehensive evaluation capabilities for testing agent performance with both regular and edge case scenarios.

### Running Evaluations

#### Prerequisites
- Python virtual environment with dependencies installed
- Configure `GEMINI_API_KEY` and `LANGFUSE_PUBLIC_KEY` environment variables

#### Regular Evaluations
```bash
uv run python -m evals.run_evals --agent "ResumeCriticAgent" --max-cases 1
```

#### Edge Case Evaluations
```bash
uv run python -m evals.run_evals --agent "ResumeCriticAgent" --max-cases 1 --edge-cases
```

### Regular Evaluations with LangFuse dataset
```bash
uv run python -m evals.run_evals --langfuse-dataset interviewready_cases --max-cases 1
```

### Edge Case Evaluations with LangFuse dataset
```bash
uv run python -m evals.run_evals --langfuse-dataset interviewready_edge_cases --max-cases 1 --edge-cases
```


#### Available Agents
- `ResumeCriticAgent` - Evaluates structural quality and ATS readability
- `ContentStrengthAgent` - Analyzes skills, achievements, and content effectiveness  
- `JobAlignmentAgent` - Semantic matching with job descriptions
- `InterviewCoachAgent` - Role-specific interview preparation

#### Command Options
- `--agent` - Comma-separated agent names to run
- `--max-cases` - Limit number of cases to evaluate
- `--edge-cases` - Run edge case scenarios instead of regular cases
- `--run-name` - Override run name for Langfuse tracking
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
