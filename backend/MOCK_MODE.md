# Agent Mock Responses

Mocking is configured per-agent using inline class variables inside each agent file.

## Toggle per agent

Example pattern used in each agent:

```python
USE_MOCK_RESPONSE = False
MOCK_RESPONSE_KEY = "ResumeCriticAgent"
```

Set `USE_MOCK_RESPONSE = True` in the agent you want to mock.

## Response source

Mock responses are loaded from:

- `backend/mock_responses.json`

The `MOCK_RESPONSE_KEY` value in each agent maps to a top-level key in that file.