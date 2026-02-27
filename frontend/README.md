# InterviewReady Frontend

## Overview

This is the React frontend for the InterviewReady application. It has been migrated from using direct Gemini API calls to using the backend API endpoints.

## Architecture

### Service Layer

The frontend uses a service layer architecture:

- **`backendService.ts`**: Main service that communicates with the backend API
- **`geminiService.ts`**: Legacy service (deprecated - kept for reference)

### API Integration

The frontend now communicates with the backend through the `/api/v1/chat` endpoint. The backend handles:
- Agent orchestration
- Session management
- Authentication
- SHARP governance compliance

## Run Locally

**Prerequisites:** Node.js, Backend server running

1. Install dependencies:
   ```bash
   npm install
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your backend URL
   ```

3. Ensure backend is running on port 8080

4. Run the frontend:
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:5173`

## Testing

### Running Tests

The frontend uses Vitest for testing. To run tests:

1. Run all tests:
   ```bash
   npm run test
   ```

2. Run tests with UI:
   ```bash
   npm run test:ui
   ```

### Test Structure

- **`tests/backendService.test.js`**: Tests for backend service integration
- Tests verify API connectivity and session management
- Tests require backend server running on port 8080

### Writing Tests

Test files should follow the naming convention `*.test.js` or `*.test.ts` and be placed in the `tests/` directory.

Example test structure:
```javascript
import { describe, it, expect } from 'vitest';

describe('Service Name', () => {
  it('should perform expected behavior', async () => {
    // Test implementation
    expect(result).toBeDefined();
  });
});
```

## Service Migration

### From geminiService to backendService

The migration involved:

1. **Service Creation**: Created `backendService.ts` with API integration
2. **Import Updates**: Updated `App.tsx` to use new service
3. **API Communication**: All agent calls now go through backend `/chat` endpoint
4. **Session Management**: Added session ID handling for backend state management
5. **Authentication**: Added token-based authentication support

### Key Differences

| Aspect | geminiService | backendService |
|--------|---------------|----------------|
| API Calls | Direct Gemini API | Backend `/api/v1/chat` |
| Authentication | API Key | JWT Token |
| Session Management | None | Backend-managed sessions |
| Error Handling | Basic | Enhanced with backend error codes |
| SHARP Compliance | Not implemented | Built-in to backend |

## Agent Functions

All agent functions maintain the same interface:

```typescript
// Resume extraction
extractorAgent(input: string | ExtractorFileData): Promise<Resume>

// Resume critique
resumeCriticAgent(resume: Resume): Promise<StructuralAssessment>

// Content analysis
contentStrengthAgent(resume: Resume): Promise<ContentAnalysisReport>

// Job alignment
alignmentAgent(resume: Resume, jd: string): Promise<AlignmentReport>

// Interview coaching
interviewCoachAgent(alignment: AlignmentReport, history: ChatMessage[]): Promise<string>
```

## Troubleshooting

### Common Issues

1. **CORS Errors**: Ensure backend allows frontend origin (configured for localhost:5173)
2. **Authentication Errors**: Check token configuration in backend
3. **Backend Unavailable**: Verify backend is running on port 8080
4. **API Timeouts**: Check backend performance and network connectivity

### Environment Variables

- `REACT_APP_API_URL`: Backend API URL (default: http://localhost:8080)
