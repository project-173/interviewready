# InterviewReady Backend

Production-ready Python FastAPI backend with multi-agent AI orchestration for resume optimization.

## Architecture

This Python backend provides a comprehensive API for resume analysis through specialized AI agents:

- **FastAPI** - High-performance async web framework with automatic API documentation
- **Multi-Agent System** - Specialized agents for resume critique, content analysis, job alignment, and interview coaching
- **Google Gemini Integration** - LLM-powered analysis with structured responses
- **SQLAlchemy** - Database ORM with async support
- **Pydantic V2** - Data validation and serialization with type safety
- **Structured Logging** - Complete request traceability with JSON logging
- **SHARP Governance** - Decision transparency and analysis framework

## Setup

### Prerequisites

- Python 3.11+
- uv package manager

### Installation

1. Install dependencies:
```bash
uv sync
```

2. Configure environment:
```bash
cp .env.example .env
```

3. Update `.env` with your Google AI credentials and other configuration.

### Running the Application

```bash
uv run python -m app.main
```

The API will be available at `http://localhost:8000`

## API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Core Endpoints

### Chat Endpoint
- `POST /api/v1/chat?sessionId=<session-id>`

The main endpoint for interacting with AI agents. The system automatically routes requests to the appropriate agent based on intent analysis.

#### Request Format
```json
{
  "message": "Review my resume for ATS issues and suggest improvements."
}
```

#### Response Format
```json
{
  "agent_name": "ResumeCriticAgent",
  "content": "Analysis results (JSON or text based on agent type)",
  "reasoning": "Brief explanation of the analysis approach",
  "confidence_score": 0.9,
  "decision_trace": [
    "Orchestrator: Routed to ResumeCriticAgent based on intent analysis."
  ],
  "sharp_metadata": {
    "analysis_type": "resume_critique",
    "governance_score": 0.85
  }
}
```

## Agent System

### Available Agents

1. **ResumeCriticAgent**
   - Analyzes resume structure and ATS readability
   - Provides formatting and content organization recommendations
   - Returns markdown-formatted critique

2. **ContentStrengthAgent**
   - Evaluates skills, achievements, and content effectiveness
   - Identifies strengths and improvement opportunities
   - Returns JSON with detailed analysis

3. **JobAlignmentAgent**
   - Performs semantic matching with job descriptions
   - Calculates fit scores and identifies gaps
   - Returns JSON with alignment analysis

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
