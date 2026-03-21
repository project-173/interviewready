# InterviewReady Frontend

Modern React TypeScript application for AI-powered resume optimization and interview preparation.

## Overview

The InterviewReady frontend provides an intuitive interface for interacting with specialized AI agents that analyze resumes, align them with job descriptions, and provide interview coaching. The application communicates with a comprehensive backend API that handles multi-agent orchestration and session management.

## Architecture

### Technology Stack

- **React 18** - Modern UI framework with hooks and concurrent features
- **TypeScript** - Type-safe development with enhanced developer experience
- **Vite** - Fast build tool and development server
- **TailwindCSS** - Utility-first CSS framework for rapid styling
- **Vitest** - Fast unit testing framework

### Application Structure

The frontend follows a service-oriented architecture with clear separation of concerns:

- **Service Layer**: API communication and data management
- **Component Layer**: Reusable UI components
- **Application Layer**: Main application logic and state management

## Setup

### Prerequisites

- Node.js 18+
- Backend server running on port 8000

### Installation

1. Install dependencies:
```bash
npm install
```

2. Configure environment:
```bash
cp .env.example .env
```

3. Update `.env` with your backend URL:
```
VITE_API_BASE_URL=http://localhost:8000
```

### Running the Application

1. Ensure the backend is running on port 8000
2. Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:3000`

## Core Features

### Multi-Agent Interface

The frontend provides seamless interaction with four specialized AI agents:

1. **Resume Critic**: Structural analysis and ATS optimization recommendations
2. **Content Strength**: Skills and achievements analysis with improvement suggestions
3. **Job Alignment**: Semantic matching with job descriptions and fit scoring
4. **Interview Coach**: Role-specific interview preparation and coaching

### Session Management

- Persistent sessions across browser refreshes
- Automatic session creation and tracking
- Context preservation for multi-turn conversations
- Real-time response streaming

### User Experience

- Responsive design for desktop and mobile devices
- Intuitive workflow guidance with step indicators
- Real-time loading states and progress feedback
- Error handling with user-friendly messages

## Project Structure

```
frontend/
├── components/              # Reusable UI components
│   ├── ResumePreview.tsx   # Resume display component
│   ├── StepIndicator.tsx   # Workflow progress indicator
│   └── WorkflowSteps.tsx   # Step-by-step guidance
├── tests/                  # Test suite
│   └── backendService.test.js
├── App.tsx                 # Main application component
├── backendService.ts       # Backend API integration
├── geminiService.ts        # Legacy service (deprecated)
├── types.ts                # TypeScript type definitions
├── index.html              # HTML template
├── index.tsx               # Application entry point
├── vite.config.ts          # Vite configuration
└── package.json            # Dependencies and scripts
```

## API Integration

### Backend Service

The `backendService.ts` module handles all communication with the backend API:

```typescript
// Main chat endpoint
const response = await backendService.chat(message, sessionId);

// Session management
const session = await backendService.createSession();
```

### Response Handling

The frontend processes structured responses from different agents:

- **Text Responses**: Markdown rendering for critique and coaching
- **JSON Responses**: Structured data display for analysis results
- **Error Handling**: Graceful degradation with user-friendly error messages

## Testing

### Running Tests

1. Run all tests:
```bash
npm run test
```

2. Run tests with UI:
```bash
npm run test:ui
```

3. Run tests in watch mode:
```bash
npm run test:watch
```

### Test Structure

- **Unit Tests**: Component logic and service functions
- **Integration Tests**: API communication and data flow
- **Mock Tests**: Development with simulated backend responses

### Writing Tests

Test files should follow the naming convention `*.test.js` or `*.test.ts`:

```javascript
import { describe, it, expect } from 'vitest';

describe('Component/Service Name', () => {
  it('should perform expected behavior', async () => {
    // Test implementation
    expect(result).toBeDefined();
  });
});
```

## Development Workflow

### Component Development

1. Create components in the `components/` directory
2. Use TypeScript for type safety
3. Follow React best practices with hooks
4. Implement responsive design with TailwindCSS

### API Integration

1. Use `backendService.ts` for all API calls
2. Handle loading states and errors appropriately
3. Implement proper TypeScript types for responses
4. Test with both real and mock backend responses

### Styling Guidelines

- Use TailwindCSS utility classes for styling
- Implement responsive design with mobile-first approach
- Follow consistent spacing and color schemes
- Ensure accessibility with proper ARIA labels

## Environment Variables

- `VITE_API_BASE_URL`: Backend API URL (default: `http://localhost:8000`)

## Troubleshooting

### Common Issues

1. **CORS Errors**: Ensure backend allows frontend origin (localhost:3000)
2. **Authentication Errors**: Verify backend authentication configuration
3. **Backend Unavailable**: Check if backend is running on port 8000
4. **API Timeouts**: Verify backend performance and network connectivity

### Development Tips

- Use browser dev tools to inspect API requests and responses
- Check the console for detailed error messages
- Use the React Developer Tools extension for component debugging
- Test with different screen sizes for responsive design validation
