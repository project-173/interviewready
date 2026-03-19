# Using @observe for Structured Observation Tracking

## Overview

The `@observe` decorator adds **semantic structure** to your Langfuse traces, making it easier to:
- Distinguish agent decisions from utility functions from safety checks
- Filter traces by observation type in Langfuse UI
- Correlate failures to specific categories (tool failures vs guardrail blocks)

## Quick Start

### 1. Import the decorator
```python
from app.core.langfuse_client import observe
```

### 2. Decorate functions with observation types
```python
# Agent-level decision
@observe(name="resume-evaluator", observation_type="agent")
def evaluate_resume(resume, jd):
    pass

# Utility function
@observe(name="pdf-parser", observation_type="tool")
def parse_pdf(file):
    pass

# Safety check
@observe(name="hallucination-guard", observation_type="guardrail")
def check_hallucinations(text):
    pass
```

## Observation Types

| Type | Use Case | Example |
|------|----------|---------|
| **agent** | High-level decisions | Resume matching, candidate ranking |
| **tool** | Utility functions | PDF parsing, data extraction |
| **guardrail** | Safety/quality gates | Hallucination detection, bias checking |
| **generation** | LLM calls | OpenAI completions |
| **retrieval** | Data lookups | Vector store queries |

## Integration Examples

### Example 1: Existing Agent with @observe

Before (using `@trace_agent_process`):
```python
# app/agents/resume_critic.py
from app.core.langfuse_client import trace_agent_process

class ResumeCriticAgent:
    @trace_agent_process
    def process(self, input_text, context):
        ...
```

After (mixing both):
```python
from app.core.langfuse_client import trace_agent_process, observe

class ResumeCriticAgent:
    @trace_agent_process
    def process(self, input_text, context):
        # High-level orchestration is traced automatically
        return self._evaluate_resume(input_text)
    
    @observe(name="resume-evaluation", observation_type="agent")
    def _evaluate_resume(self, resume_text):
        # Sub-decision tracked as agent observation
        ...
```

**In Langfuse:**
```
trace: ResumeCriticAgent_process (session_id=abc)
  ├─ observation: resume-evaluation (type=agent)
  │   ├─ observation: extract-skills (type=tool)
  │   ├─ observation: validate-facts (type=guardrail)
  │   └─ output: {...}
```

---

### Example 2: Tools with @observe

```python
from app.core.langfuse_client import observe
from app.utils.pdf_parser import extract_text

@observe(name="extract-resume-text", observation_type="tool")
def load_resume(file_path: str) -> str:
    """Tool observation: marks data extraction as separate step."""
    return extract_text(file_path)

@observe(name="extract-sections", observation_type="tool")
def parse_resume_sections(text: str) -> dict:
    """Parse into experience, skills, education."""
    return {
        "experience": _extract_experience(text),
        "skills": _extract_skills(text),
        "education": _extract_education(text),
    }
```

**Usage in agents:**
```python
@observe(name="resume-review", observation_type="agent")
def review_resume(file_path: str):
    # Tool calls are automatically traced
    text = load_resume(file_path)
    sections = parse_resume_sections(text)
    
    # Make decision
    return make_decision(sections)
```

**Result in Langfuse:**
```
trace: review_resume (session_id=abc)
  ├─ observation: extract-resume-text (type=tool)
  ├─ observation: extract-sections (type=tool)
  │   └─ (child tools visible here)
  └─ output: {...}
```

---

### Example 3: Guardrails with @observe

```python
from app.core.langfuse_client import observe

@observe(name="validate-confidence", observation_type="guardrail")
def check_confidence(decision: dict, threshold: float = 0.5) -> bool:
    confidence = decision.get("confidence", 0)
    if confidence < threshold:
        raise ValueError(f"Confidence {confidence} below threshold {threshold}")
    return True

@observe(name="detect-bias", observation_type="guardrail")
def detect_bias(response: str, protected_attrs: list) -> dict:
    """Scan response for biased language."""
    flags = []
    for attr in protected_attrs:
        if _contains_biased_language(response, attr):
            flags.append(attr)
    return {"has_bias": len(flags) > 0, "flags": flags}

@observe(name="hallucination-check", observation_type="guardrail")
def validate_grounding(response: str, sources: list) -> bool:
    """Ensure response is grounded in sources (prevent hallucinations)."""
    for claim in _extract_claims(response):
        if not _is_in_sources(claim, sources):
            return False
    return True
```

**Usage in API endpoint:**
```python
from app.core.langfuse_client import observe

@observe(name="chat-request", observation_type="agent")
async def chat_endpoint(request, session_id):
    # Run orchestration
    response = orchestrator.orchestrate(request)
    
    # Apply guardrails
    check_confidence(response)
    validate_grounding(response.content, response.sources)
    detect_bias(response.content, ["gender", "age"])
    
    return response
```

**Result:**
```
trace: chat-request (session_id=abc, type=agent)
  ├─ observation: detect-bias (type=guardrail) → passed
  ├─ observation: validate-grounding (type=guardrail) → passed
  ├─ observation: validate-confidence (type=guardrail) → passed
  └─ output: {...}
```

---

### Example 4: OpenAI Integration

```python
from app.core.langfuse_client import observe
from openai import OpenAI

client = OpenAI()

@observe(name="generate-coaching-advice", observation_type="agent")
def coach_candidate(resume: dict, feedback: str) -> str:
    """Use LLM to generate coaching advice."""
    
    # This will be tracked if you use Langfuse's OpenAI wrapper
    # For now, wrap manually:
    return _generate_with_llm(resume, feedback)

def _generate_with_llm(resume: dict, feedback: str) -> str:
    """Internal LLM call (would use Langfuse OpenAI async wrapper in production)."""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": "You are an interview coach."
            },
            {
                "role": "user",
                "content": f"Resume: {resume}\nFeedback: {feedback}\nProvide coaching advice."
            }
        ]
    )
    return response.choices[0].message.content
```

**Note:** For full OpenAI integration, use `from langfuse.openai import openai` which automatically traces completions in Langfuse.

---

## Filtering in Langfuse UI

Once observations are tagged with types, you can filter traces:

**Example filters:**
- `observation_type:agent` → Show only agent decisions
- `observation_type:tool` → Show all tool calls (debugging tool performance)
- `observation_type:guardrail` → Show all safety checks (compliance audit)
- `observation_type:guardrail AND observation_type.has_bias:true` → Show bias guardrail failures

---

## Complete Workflow Example

```python
# app/api/v1/endpoints/chat.py
from app.core.langfuse_client import observe, langfuse

@observe(name="chat-session", observation_type="agent")
async def chat_endpoint(request, session_id):
    """Full chat workflow with observations."""
    
    with langfuse.propagate_attributes(sessionId=session_id):
        with langfuse.trace(name="chat_api_request") as trace:
            
            # Step 1: Extract and parse input (tool)
            resume_data = load_resume(request.resume)
            
            # Step 2: Make matching decision (agent)
            match_decision = evaluate_resume_fit(resume_data, request.job_description)
            
            # Step 3: Generate coaching (agent + tool)
            coaching = generate_coaching_advice(resume_data, match_decision)
            
            # Step 4: Apply safety gates (guardrails)
            validate_answer(coaching)  # confidence check
            check_no_bias(coaching)    # bias detection
            verify_grounded(coaching)  # hallucination check
            
            trace.update(output={
                "match": match_decision,
                "coaching": coaching,
                "passed_guardrails": True,
            })
            
            return ChatResponse(...)
```

**Trace Structure in Langfuse:**
```
trace: chat_api_request (session_id=xyz)
  ├─ observation: load-resume (type=tool)
  ├─ observation: evaluate-resume-fit (type=agent)
  ├─ observation: generate-coaching (type=agent)
  │   └─ (LLM call tracked here)
  ├─ observation: validate-answer (type=guardrail)
  ├─ observation: check-no-bias (type=guardrail)
  ├─ observation: verify-grounded (type=guardrail)
  └─ output: {...}
```

---

## Migration Path

1. **Keep existing `@trace_agent_process`** on agent `.process()` methods
2. **Add `@observe`** to inner methods and utilities
3. **Result:** Nested observations within traces (best of both)

**Before:**
```python
@trace_agent_process
def process(...):
    pass
```

**After:**
```python
@trace_agent_process
def process(...):
    return self._inner_logic()

@observe(name="inner-logic", observation_type="agent")
def _inner_logic(self):
    pass
```

---

## Configuration

If Langfuse isn't installed or configured, `@observe` degrades gracefully:
- It will attempt to use Langfuse's `@observe`
- Falls back to local tracing using `langfuse.trace()`
- No errors if Langfuse is missing

---

## See Also

- [Examples](app/agents/examples_observe.py)
- [Langfuse @observe docs](https://langfuse.com/docs/python-sdk#observe-decorator)
- [GOVERNANCE.md](GOVERNANCE.md) - Guardrail examples
