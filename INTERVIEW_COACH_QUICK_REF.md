# Interview Coach - Quick Reference

## Summary of Changes ✓

The InterviewCoachAgent now asks **one question at a time** instead of providing multiple questions at once.

## How It Works

### State Flow
```
New Session
    ↓
interview_active = false
    ↓
Initialize Interview (Q 0 of 5)
    ↓
Ask Question 1
    ↓
[User responds]
    ↓
Store Answer, Advance to Q1
    ↓
Provide Feedback + Ask Question 2
    ↓
[Repeat until Q5]
    ↓
Interview Complete
```

## API Usage

### First Call (Empty History)
```python
request = {
    "intent": "INTERVIEW_COACH",
    "resumeData": {...},
    "jobDescription": "...",
    "messageHistory": []  # Empty = first question
}
```
**Returns:** Question 1/5

### Follow-up Call (With Answer)
```python
request = {
    "intent": "INTERVIEW_COACH",
    "resumeData": {...},
    "jobDescription": "...",
    "messageHistory": [
        {"role": "agent", "text": "Tell me about..."},
        {"role": "user", "text": "I did..."}  # User's answer
    ]
}
```
**Returns:** Feedback + Question 2/5

## New Methods Added

| Method | Purpose |
|--------|---------|
| `_init_interview_session()` | Initialize state on first call |
| `_get_interview_state()` | Retrieve current progress |
| `_store_answer_and_advance()` | Save answer, move to next question |
| `_build_interview_prompt()` | Create context-aware prompt for Gemini |

## JSON Response Format

```json
{
  "current_question_number": 1,
  "total_questions": 5,
  "interview_type": "behavioral",
  "question": "The actual question",
  "keywords": ["key1", "key2"],
  "tip": "How to answer this",
  "feedback": "On previous answer (blank if first Q)",
  "next_challenge": "Focus area"
}
```

## State Storage Location

**Where:** `SessionContext.shared_memory` dictionary
**Persists:** Across multiple calls with same session_id
**When created:** First call (message_history empty)
**Reset:** When new session_id used

## Configuration

To change total questions (default 5):
```python
# In _init_interview_session()
context.shared_memory["total_questions"] = 10
```

## Testing

```bash
# Run full test suite
python -m pytest tests/test_agents.py -v

# Test with mock mode
python test_mock_mode.py
```

## Debugging

Enable debug logs:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Look for these patterns:
# "First question of interview"
# "Stored user answer and advanced"
# "Processing interview question X of Y"
```

## Examples

### Example 1: First Question
```
User: Resume + Job Description (no history)
System: Initializes interview, question_index = 0
Response: Q1/5 "Tell me about your background..."
```

### Example 2: Follow-up
```
User: Previous question + their answer + history
System: Stores answer at index 0, advances to index 1
Response: Feedback on their answer + Q2/5 "That's great..."
```

### Example 3: Interview End (after Q5)
```
User: Answer to Q5 + full history
System: Stores answer at index 4, question_index = 5 (end)
Response: Final feedback, interview complete
```

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Not ⏭️ progressing to next Q | Check message_history format |
| Same question asked twice | Verify advancing happens |
| No feedback on 2nd+ answer | Ensure history includes 1st Q |
| State reset unexpectedly | Check session_id unchanged |
| Gemini response parsing fails | Check JSON format matches |

## File Locations

- **Implementation:** `backend/app/agents/interview_coach.py`
- **Documentation:** `INTERVIEW_COACH_MODIFICATION.md`
- **Tests:** `backend/tests/test_agents.py`
- **Mock responses:** `backend/app/mock_responses.json`

## Backward Compatibility

✅ Old tests still work
✅ Mock mode preserved
✅ Gemini Live integration unchanged
✅ Other agents unaffected
✅ Empty message_history = first question (no breaking changes)

## Key Metrics in Response

Each response now includes:
- `current_question_number`: 1-5
- `total_questions`: 5 (or configured value)
- `sharp_metadata.current_question_number`: For audit trail
- `sharp_metadata.total_questions`: For audit trail

Use these to display progress to user: "Question 2 of 5"

---

**Last Updated:** March 2026
**Status:** Ready for testing
**Breaking Changes:** None
