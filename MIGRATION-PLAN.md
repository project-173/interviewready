# Java to Python Backend Migration Plan

## 1. Executive Summary

This document outlines the plan to migrate the existing Java-based backend to a new Python-based backend. The goal is to replicate all existing functionalities while leveraging the strengths of the Python ecosystem for AI and machine learning development. The new backend will be developed in the `backend` directory.

## 2. Proposed Python Architecture

The new backend will be built using a modern Python stack:

- **Web Framework:** **FastAPI** will be used for creating the REST API. Its asynchronous capabilities and Pydantic-based data validation make it an excellent choice for high-performance AI applications.
- **Orchestration:** **LangGraph** will be used to manage the multi-agent workflows, providing a clear and maintainable way to define the agentic pipeline.
- **AI/LLM Integration:** The **Google AI Python SDK** (`google-generativeai`) will be used for direct communication with the Gemini models.
- **Data Models:** **Pydantic** will be used for all data schemas, ensuring type safety and easy serialization/deserialization.
- **Authentication:** **Firebase Admin Python SDK** will be used to replicate the existing Firebase-based authentication.
- **Persistence:** **SQLAlchemy** will be used as the ORM (Object-Relational Mapper) to interact with the database. **Alembic** will be used for managing database migrations.
- **Containerization:** A new **Dockerfile** will be created for the Python backend, and the `docker-compose.yaml` will be updated.

## 3. Migration Phases

The migration will be executed in the following phases:

### Phase 1: Project Setup and Core Infrastructure

1.  **Create Project Structure:** Create the `backend` directory with subdirectories for `app`, `agents`, `core`, `models`, `tests`, etc.
2.  **Dependency Management:** Create a `pyproject.toml` file to manage project dependencies with `uv`.
3.  **FastAPI Application:** Set up the main FastAPI application, including the configuration for database and AI services.
4.  **Authentication:** Implement a middleware for FastAPI to handle Firebase authentication, mirroring the logic in `FirebaseAuthenticationFilter.java`.

### Phase 2: Data Models and Persistence

1.  **Pydantic Schemas:** Translate all Java models from `com.agent.backend.model` into Pydantic schemas.
2.  **SQLAlchemy Models:** Create SQLAlchemy ORM models corresponding to the Pydantic schemas.
3.  **Database Migrations:** Use Alembic to generate initial database migrations based on the SQLAlchemy models.

### Phase 3: Agent Migration

Each agent will be re-implemented in Python, leveraging LangGraph for state management and execution flow while preserving the exact logic from the Java implementations.

#### 3.1 Base Agent Architecture
1. **Abstract Base Agent:** Create `BaseAgent` abstract class equivalent to Java `AbstractAgent`
2. **Agent Interface:** Implement `BaseAgentProtocol` matching Java `BaseAgent` interface
3. **Gemini Integration:** Create `GeminiService` to replace Spring AI ChatClient
4. **Response Builder:** Implement `AgentResponseBuilder` for consistent response creation

#### 3.2 Individual Agent Implementation
1. **`ExtractorAgent`:** Create Python equivalent for resume parsing (if exists in Java)
2. **`ResumeCriticAgent`:** Migrate with identical system prompt and confidence scoring (0.9)
3. **`ContentStrengthAgent`:** Full migration with:
   - Complete system prompt preservation
   - JSON parsing logic with regex fallback
   - Confidence calculation algorithms
   - Hallucination risk assessment
   - Evidence strength classification
4. **`JobAlignmentAgent`:** Migrate with alignment evaluation logic (0.88 confidence)
5. **`InterviewCoachAgent`:** Migrate with:
   - GeminiLiveService integration
   - Audio preview model support
   - Fallback error handling

#### 3.3 Agent Logic Preservation
- **System Prompts:** Exact copy from Java implementations
- **Confidence Scores:** Preserve original scoring logic
- **Decision Traces:** Maintain audit trail format
- **SHARP Metadata:** Keep governance data structure
- **Error Handling:** Replicate exception handling patterns

### Phase 4: Orchestration and Governance

1.  **Orchestrator:** Create an orchestration layer using LangGraph to replicate the logic of `OrchestrationAgent.java`. This will include the intent analysis to route requests to the correct agent or chain of agents.
2.  **Governance Service:** Port the `SharpGovernanceService.java` to a Python module. This will involve translating the logic for hallucination checks, confidence scoring, and other validation rules.

### Phase 5: API Endpoints

Re-create the API endpoints from `AgentController.java` using FastAPI.

1.  `/api/v1/chat`: The main endpoint for interacting with the agentic system.
2.  `/api/v1/agents`: The endpoint for listing the available agents and their system prompts.

### Phase 6: Testing

1.  **Unit Tests:** Write unit tests for individual agents, services, and helper functions.
2.  **Integration Tests:** Create integration tests for the API endpoints and the full agentic workflow.

### Phase 7: Containerization

1.  **Dockerfile:** Create a `Dockerfile` for the Python backend.
2.  **Docker Compose:** Update the `docker-compose.yaml` to run the new Python backend alongside the frontend and any other services.

## 4. Clarification Questions

Before proceeding, I would like to clarify the following:

1.  Is the database schema defined by the JPA entities in the Java code the source of truth, or is there an existing database that I need to connect to and inspect?
2.  Are there any implicit requirements or business logic not explicitly captured in the Java code that I should be aware of?
3.  The `InterviewCoachAgent` uses a `GeminiLiveService`. Is there a specific Python library or implementation pattern you prefer for this real-time interaction?

Once I receive your feedback on this plan and the clarification questions, I will begin with Phase 1.
