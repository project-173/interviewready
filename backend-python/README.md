# InterviewReady Backend - Python

Production-Ready Multi-Agent AI Backend with Gemini and Firebase.

## Architecture

This Python backend is built using:

- **FastAPI** - High-performance web framework
- **LangGraph** - Multi-agent workflow orchestration  
- **Google Generative AI** - Gemini model integration
- **Firebase Admin** - Authentication and user management
- **SQLAlchemy** - Database ORM
- **Pydantic** - Data validation and serialization

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Firebase project with service account

### Installation

1. Install dependencies with uv:
```bash
uv sync
```

2. Copy environment configuration:
```bash
cp .env.example .env
```

3. Update `.env` with your Firebase and Google AI credentials.

### Running the Application

```bash
uv run python -m app.main
```

The API will be available at `http://localhost:8000`

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
backend-python/
├── app/
│   ├── agents/          # Agent implementations
│   ├── api/            # API endpoints
│   ├── core/           # Configuration and utilities
│   ├── models/         # Data models
│   ├── storage/        # Database operations
│   └── utils/          # Helper functions
├── tests/              # Test suite
└── pyproject.toml      # Project configuration
```

## Migration Status

This is the Python migration of the original Java backend. See [MIGRATION-PLAN.md](../MIGRATION-PLAN.md) for details.

**Phase 1 Complete**: ✅ Project setup and core infrastructure
- ✅ Directory structure created
- ✅ Dependency management (pyproject.toml)  
- ✅ FastAPI application setup
- ✅ Firebase authentication middleware

**Next Phases**: Data models, Agent migration, Orchestration, API endpoints, Testing, Containerization
