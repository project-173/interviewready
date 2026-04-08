# Interview Coach Agent - One Question at a Time Implementation

## Overview

The InterviewCoachAgent has been successfully modified to ask one interview question at a time, simulating a realistic interview process. This enables progressive training where the agent provides feedback on each answer before asking the next question.

## Key Features

### 1. **Progressive Question Flow**
- **First Message**: User provides resume and job description → Agent asks Question 1
- **Subsequent Messages**: User answers → Agent provides feedback → Agent asks Question 2, etc.
- **Total Questions**: Configured to 5 questions per interview session (configurable)
- **Progress Tracking**: Each response includes current question number and total questions

### 2. **Interview State Management**
Interview state is stored in `SessionContext.shared_memory` and persists across multiple API calls:
- `interview_active`: Boolean flag indicating active interview session
- `current_question_index`: Current question (0-4 for 5 questions)
- `asked_questions`: List of all questions asked so far
- `user_answers`: List of all user answers provided
- `total_questions`: Total questions in the interview (default: 5)

### 3. **New JSON Response Format**
The agent now returns a single question response:
```json
{
  "current_question_number": 1,
  "total_questions": 5,
  "interview_type": "behavioral|technical|situational|competency",
  "question": "Specific interview question tailored to candidate",
  "keywords": ["keyword1", "keyword2"],
  "tip": "Guidance on how to approach this question",
  "feedback": "Constructive feedback on previous answer (if follow-up)",
  "next_challenge": "Focus area for next question"
}
```

## Implementation Details

### Modified Methods

#### `_init_interview_session(context: SessionContext) -> None`
Initializes interview state on first call. Sets up:
- Interview active flag
- Question index to 0
- Empty lists for questions and answers
- Total questions to 5

#### `_get_interview_state(context: SessionContext) -> dict`
Retrieves current interview state from shared memory. Returns safe defaults if state doesn't exist.

#### `_store_answer_and_advance(user_answer: str, context: SessionContext) -> None`
- Stores user's answer to current question
- Advances question index by 1
- Used when processing follow-up responses

#### `_build_interview_prompt(input_data: AgentInput, context: SessionContext, user_answer: Optional[str]) -> str`
Builds context-aware prompt that includes:
- Resume information
- Job description
- Current interview progress
- Previous questions (for context)
- User's current answer (for feedback)

### Updated Process Method
The main `process()` method now:
1. Detects if this is first call or follow-up by checking `message_history` length
2. Initializes session on first call
3. Stores answer and advances on subsequent calls  
4. Builds rich context prompt for Gemini
5. Includes interview progress in metadata

## API Usage Flow

### First Request
```
POST /api/v1/chat?sessionId=session123

{
  "intent": "INTERVIEW_COACH",
  "resumeData": { "work": [...], ... },
  "jobDescription": "Senior Software Engineer...",
  "messageHistory": []
}
```

**Response:**
```json
{
  "agent": "InterviewCoachAgent",
  "payload": {
    "current_question_number": 1,
    "total_questions": 5,
    "interview_type": "behavioral",
    "question": "Tell me about your experience leading a team...",
    "keywords": ["leadership", "team management", "challenges"],
    "tip": "Use the STAR method: Situation, Task, Action, Result",
    "feedback": "",
    "next_challenge": "Focus on measurable impact"
  }
}
```

### Follow-up Request (User's Answer)
```
POST /api/v1/chat?sessionId=session123

{
  "intent": "INTERVIEW_COACH",
  "resumeData": { "work": [...], ... },
  "jobDescription": "Senior Software Engineer...",
  "messageHistory": [
    {
      "role": "agent",
      "text": "Tell me about your experience leading a team..."
    },
    {
      "role": "user",
      "text": "I led a team of 5 engineers at Tech Corp. We implemented a microservices architecture that reduced deployment time by 40%..."
    }
  ]
}
```

**Response:**
```json
{
  "agent": "InterviewCoachAgent",
  "payload": {
    "current_question_number": 2,
    "total_questions": 5,
    "interview_type": "technical",
    "question": "Describe the technical challenges you faced when implementing that microservices architecture...",
    "keywords": ["microservices", "technical challenges", "problem-solving"],
    "tip": "Be specific about the challenges and your solutions",
    "feedback": "Great job providing a concrete example! Your STAR method was clear. For the next question, dig deeper into the technical aspects.",
    "next_challenge": "Explain technical decision-making process"
  }
}
```

## Session Persistence

The interview session persists for the same `sessionId`. Each request:
1. Retrieves the current session context
2. Checks interview state from `shared_memory`
3. Updates state based on user's response
4. Returns next question

**Session expires when:**
- User closes the session
- New session ID is provided
- Backend session is cleared (configurable TTL)

## Integration with Frontend

The frontend should:
1. **First call**: Send resume + job description with empty message history
2. **Subsequent calls**: Build message history with alternating agent/user messages
3. **Display**: Show current progress (Question 1 of 5)
4. **Input**: Get user's answer to display question
5. **Feedback**: Display feedback from previous question

### Example Frontend Implementation
```typescript
// First question
const firstResponse = await api.chat({
  intent: 'INTERVIEW_COACH',
  resumeData: resume,
  jobDescription: jobDesc,
  messageHistory: []
});

// Display first question
displayQuestion(firstResponse.payload.question);
displayTip(firstResponse.payload.tip);
displayProgress(firstResponse.payload.current_question_number, firstResponse.payload.total_questions);

// User answers question
const userAnswer = "...user's response...";

// Second question request
const secondResponse = await api.chat({
  intent: 'INTERVIEW_COACH',
  resumeData: resume,
  jobDescription: jobDesc,
  messageHistory: [
    { role: 'agent', text: firstResponse.payload.question },
    { role: 'user', text: userAnswer }
  ]
});

// Display feedback from previous answer
displayFeedback(secondResponse.payload.feedback);

// Display next question
displayQuestion(secondResponse.payload.question);
displayProgress(secondResponse.payload.current_question_number, secondResponse.payload.total_questions);
```

## Configuration

### Changing Total Questions
Edit in `interview_coach.py`:
```python
def _init_interview_session(self, context: SessionContext) -> None:
    if context.shared_memory is None:
        context.shared_memory = {}
    
    context.shared_memory["total_questions"] = 10  # Change from 5 to 10
```

### Interview Types
Questions are adaptively generated across different types:
- **Behavioral**: "Tell me about a time when..."
- **Technical**: "Explain how you would implement..."
- **Situational**: "How would you handle..."
- **Competency**: "What's your experience with..."

The agent automatically selects appropriate question types based on the resume and job description.

## Testing

Run the existing test suite:
```bash
cd backend
python -m pytest tests/test_agents.py -v -k interview
```

Or test manually:
```bash
python test_mock_mode.py
```

## Data Flow Diagram

```
User Request (Question 1)
    ↓
SessionContext.shared_memory empty?
    ↓ Yes → Initialize Session
    ↓
Build Prompt with Resume + Job Desc
    ↓
Call Gemini with System Prompt
    ↓
Parse JSON Response
    ↓
Return Single Question (Q1/5)
    ↓
User Request (Answer + Question 2)
    ↓
SessionContext.shared_memory exists
    ↓
Store User Answer
    ↓
Advance to Question Index 1
    ↓
Build Prompt with Previous Questions + Answer
    ↓
Call Gemini with System Prompt
    ↓
Parse JSON Response with Feedback
    ↓
Return Feedback + Next Question (Q2/5)
```

## Logging

The agent logs interview progress at DEBUG level:
- Session initialization
- Answer storage and advancement
- Question index transitions
- Gemini service interactions
- Response generation

Enable debug logging to track interview flow:
```python
import logging
logger = logging.getLogger('app.agents.interview_coach')
logger.setLevel(logging.DEBUG)
```

## Error Handling

- **Invalid JSON Response**: Falls back to standard Gemini if Gemini Live fails
- **Missing State**: Safely initializes state if shared_memory is corrupted
- **Session Timeout**: Gracefully restarts interview if session expires
- **Audio Unavailable**: Falls back to text-based coaching

## Backward Compatibility

- Old tests still work (message_history empty = first question)
- Mock responses are preserved
- Gemini Live integration unchanged
- All existing agents unaffected

## Future Enhancements

1. **Question Variety**: Implement question bank to avoid repetition
2. **Adaptive Difficulty**: Adjust question difficulty based on answers
3. **Performance Scoring**: Track answer quality and provide score
4. **Follow-up Questions**: Ask clarifying questions within a topic
5. **Audio Support**: Full speech-to-text interview simulation
6. **Interview Analytics**: Provide performance report after 5 questions
7. **Question Skip**: Allow candidates to skip difficult questions
8. **Retry Logic**: Option to re-answer a question for improvement

## Troubleshooting

### Questions Not Progressing
- Check `SessionContext.shared_memory` is being persisted
- Verify `session_id` is same across requests
- Check message_history is properly formed

### Same Question Repeated
- Ensure `_store_answer_and_advance()` is called
- Verify `current_question_index` increments
- Check Gemini system prompt is loaded correctly

### Missing Feedback
- Ensure message_history includes previous exchange
- Check `user_answer` is properly extracted
- Verify Gemini response includes `feedback` field

## Contact & Support

For issues or questions about this implementation:
1. Check debug logs with `logging.DEBUG`  
2. Verify session context has shared_memory
3. Test with mock mode enabled
4. Check Gemini service connectivity
