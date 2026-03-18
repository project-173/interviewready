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

## Deployment

### Local Development
```bash
docker-compose up --build
```
- Frontend: `http://localhost:80`
- Backend: `http://localhost:8080`

### Production Deployment
Automated deployment to GCP Cloud Run via GitHub Actions. See `.github/workflows/gcp-deploy.yaml` for configuration details.
