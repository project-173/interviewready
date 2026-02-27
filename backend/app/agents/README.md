# Agent Implementation Documentation

This directory contains the Python implementation of all agents migrated from the Java backend, preserving the exact logic and behavior.

## Architecture

### Base Classes

- **`BaseAgent`**: Abstract base class equivalent to Java `AbstractAgent`
- **`BaseAgentProtocol`**: Protocol interface matching Java `BaseAgent` interface
- **`GeminiService`**: Service for Gemini API interactions replacing Spring AI ChatClient
- **`GeminiLiveService`**: Service for real-time Gemini Live API with audio support

### Agent Implementations

#### 1. ResumeCriticAgent
- **Purpose**: Analyze resume structure, ATS compatibility, and impact
- **System Prompt**: "You are an expert Resume Critic. Analyze the resume for structure, ATS compatibility, and impact."
- **Confidence Score**: 0.9 (preserved from Java)
- **Key Features**:
  - Structural analysis
  - ATS compatibility checking
  - Impact evaluation
  - SHARP compliance metadata

#### 2. ContentStrengthAgent
- **Purpose**: Analyze content strength, skills reasoning, and evidence evaluation
- **System Prompt**: Complete preservation of Java system prompt with detailed JSON output structure
- **Key Features**:
  - Evidence strength classification (HIGH/MEDIUM/LOW)
  - Faithful transformation rules (no fabrication)
  - JSON parsing with regex fallback
  - Confidence calculation algorithms
  - Hallucination risk assessment
  - Skills, achievements, and suggestions analysis

#### 3. JobAlignmentAgent
- **Purpose**: Evaluate how well a resume matches a specific job description
- **System Prompt**: "You are a Job Alignment specialist. Evaluate how well a resume matches a specific job description."
- **Confidence Score**: 0.88 (preserved from Java)
- **Key Features**:
  - Resume-to-job description alignment
  - Context-aware analysis using SessionContext
  - Enhanced input with job description when available

#### 4. InterviewCoachAgent
- **Purpose**: Provide interview coaching and simulation
- **System Prompt**: "You are an expert Interview Coach. Provide feedback and simulation for interview preparation."
- **Confidence Score**: 0.85 (preserved from Java)
- **Key Features**:
  - Gemini Live integration with audio preview model
  - Fallback to standard Gemini API
  - Real-time coaching capabilities
  - Error handling for service unavailability

## Migration Details

### Logic Preservation
- **System Prompts**: Exact copy from Java implementations
- **Confidence Scores**: Preserved original scoring (ResumeCritic: 0.9, JobAlignment: 0.88, InterviewCoach: 0.85)
- **Decision Traces**: Maintained audit trail format
- **SHARP Metadata**: Kept governance data structure
- **Error Handling**: Replicated exception handling patterns

### Key Differences from Java
1. **Service Layer**: Uses `GeminiService` instead of Spring AI ChatClient
2. **JSON Parsing**: Python `json` module with regex fallback (equivalent to Java ObjectMapper)
3. **Type Hints**: Added Python type annotations for better code clarity
4. **Async Support**: Foundation for async operations (can be extended)

### Dependencies
- `google-generativeai`: Gemini API client
- `pydantic`: Data validation and serialization
- `typing`: Type hints support
- `json`: JSON parsing and serialization
- `re`: Regular expressions for JSON extraction

## Usage Example

```python
from app.agents import ResumeCriticAgent, GeminiService
from app.models.session import SessionContext

# Initialize service and agent
gemini_service = GeminiService(api_key="your-api-key")
agent = ResumeCriticAgent(gemini_service)

# Create context
context = SessionContext(
    session_id="test_session",
    resume_data="Your resume text here"
)

# Process resume
response = agent.process("Resume content", context)
print(response.content)
```

## Testing

Run the test script to verify all agents:

```bash
cd backend
python test_agents.py
```

## Integration with LangGraph

These agents are designed to work seamlessly with LangGraph orchestration:

1. **State Management**: Each agent returns `AgentResponse` with SHARP compliance data
2. **Decision Traces**: Complete audit trails for governance
3. **Metadata**: Structured metadata for workflow coordination
4. **Error Handling**: Graceful degradation with clear error messages

## Configuration

### Environment Variables
- `GEMINI_API_KEY`: Required for Gemini API access
- `GEMINI_MODEL`: Optional model override (default: "gemini-1.5-pro")

### Model Configuration
- **Standard Gemini**: Uses "gemini-1.5-pro" by default
- **Gemini Live**: Uses "gemini-2.5-flash-native-audio-preview-12-2025" for InterviewCoachAgent

## Compliance and Governance

All agents implement SHARP principles:
- **S**afety: Input validation and error handling
- **H**allucination Detection: Risk assessment and confidence scoring
- **A**uditability: Complete decision traces
- **R**eliability: Graceful degradation and fallback mechanisms
- **P**rivacy: No data persistence beyond session context
