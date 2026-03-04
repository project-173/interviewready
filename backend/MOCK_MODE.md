# Mock Mode Configuration

## Environment Variables

To enable mock mode for all Gemini API calls, set the following environment variables:

### Enable Mock Mode
```bash
# Enable mock responses for all Gemini API calls
MOCK_GEMINI=true

# Optional: Log mock calls for debugging
LOG_MOCK_CALLS=true

# Optional: Path to custom mock responses file
MOCK_RESPONSES_FILE=./mock_responses.json
```

### Disable Mock Mode (Default)
```bash
# Use real Gemini API (requires GEMINI_API_KEY)
MOCK_GEMINI=false
GEMINI_API_KEY=your_actual_api_key_here
```

## Usage Examples

### Development/Testing
```bash
export MOCK_GEMINI=true
export LOG_MOCK_CALLS=true
cd backend && uv run fastapi dev
```

### Production
```bash
export MOCK_GEMINI=false
export GEMINI_API_KEY=your_production_api_key
cd backend && uv run fastapi dev
```

## Mock Response Behavior

When mock mode is enabled, all agents will receive predefined responses:

- **ContentStrengthAgent**: Returns structured JSON with skills, achievements, and suggestions
- **ResumeCriticAgent**: Returns detailed resume critique with ATS analysis
- **InterviewCoachAgent**: Returns interview coaching tips and practice feedback
- **JobAlignmentAgent**: Returns job fit analysis with skill matching

## Benefits of Mock Mode

1. **No API Costs**: No charges from Gemini API during development
2. **Offline Development**: Work without internet connectivity
3. **Consistent Testing**: Predictable responses for automated tests
4. **Fast Response**: No network latency for quicker development cycles

## Switching Between Modes

You can switch between mock and real API modes without restarting the application by setting the `MOCK_GEMINI` environment variable. The system will detect the change on the next agent initialization.

## Custom Mock Responses

You can provide custom mock responses via `MOCK_RESPONSES_FILE`.

The backend includes a ready-to-use example at:

- `backend/mock_responses.json`

Supported structure:

```json
{
  "agents": {
    "ContentStrengthAgent": {
      "default": { "response_json": { "skills": [], "achievements": [], "suggestions": [], "hallucinationRisk": 0.2, "summary": "" } }
    },
    "ResumeCriticAgent": {
      "default": { "response_text": "markdown/text response" }
    },
    "InterviewCoachAgent": {
      "rules": [
        {
          "when": { "user_input_contains_any": ["question", "answer"] },
          "response_text": "conditional response"
        }
      ],
      "default": { "response_text": "fallback for this agent" }
    },
    "JobAlignmentAgent": {
      "default": { "response_json": { "skillsMatch": [], "missingSkills": [], "experienceMatch": "", "fitScore": 75, "reasoning": "" } }
    }
  },
  "fallback": { "response_text": "used if agent-specific entry is missing" }
}
```
