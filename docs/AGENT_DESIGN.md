# Agent Design Documentation — InterviewReady

## 1. Overview

InterviewReady employs four specialised AI agents, each inheriting from a common `BaseAgent` abstract class and exposing a uniform `process(input_data, context) → AgentResponse` interface. Agents are invoked sequentially by the `OrchestrationAgent` through a LangGraph `StateGraph` workflow. Each agent maintains its own system prompt, confidence score, and mock-response key to enable deterministic testing without live API calls.

---

## 2. Agent Hierarchy & Shared Infrastructure

### 2.1 Class Hierarchy

```
BaseAgentProtocol (Protocol)
    └── BaseAgent (ABC)
            ├── ResumeCriticAgent
            ├── ContentStrengthAgent
            ├── JobAlignmentAgent
            └── InterviewCoachAgent
```

### 2.2 `BaseAgent` Capabilities

| Capability | Implementation |
|------------|---------------|
| System prompt management | `get_system_prompt()` / `update_system_prompt()` |
| LLM invocation | `call_gemini(input_text, context)` |
| Schema validation | `parse_and_validate(raw_result, PydanticModel)` |
| Mock responses | `get_mock_response_by_key(key)` via `mock_responses.json` |
| Security scanning | `LLMGuardScanner` (input/output) inside `call_gemini()` |
| Observability | Langfuse `start_as_current_observation` spans |
| Output sanitisation | `OutputSanitizer.sanitize()` post-LLM |

### 2.3 Shared Input/Output Contract

```python
# Input
AgentInput(
    intent: Intent,
    resume: Optional[Resume],
    resume_document: Optional[ResumeDocument],
    job_description: str,
    message_history: List[InterviewMessage],
    audio_data: Optional[bytes],
)

# Output
AgentResponse(
    agent_name: str,
    content: str,           # JSON-serialised structured result
    reasoning: str,         # human-readable explanation
    confidence_score: float,
    decision_trace: List[str],
    sharp_metadata: Dict[str, Any],
)
```

---

## 3. ResumeCriticAgent

### 3.1 Purpose

Evaluates the structural quality, ATS readability, and formatting of a resume from a recruiter's perspective.

### 3.2 Reasoning Pattern

**Analytical / rule-based LLM**. The agent applies a structured critique template and forces the LLM to output a validated JSON schema. There is no multi-step reasoning loop; a single LLM call produces the complete assessment.

### 3.3 Prompt Design

```
System:  Expert Resume Critic. You must output ONLY a JSON object matching
         StructuralAssessment schema. Anti-jailbreak directive appended.
User:    "Resume data: <JSON serialisation of Resume model>"
```

Key constraints enforced in the system prompt:
- **No markdown code fences** — prevents `parse_and_validate` failures.
- **Score must be 0–100** — enables numeric comparison in governance.
- **String arrays must contain 2+ items** — prevents trivially empty outputs.

### 3.4 Output Schema (`StructuralAssessment`)

```json
{
  "score": 75,
  "readability": "Clear section headers...",
  "formattingRecommendations": ["...", "..."],
  "suggestions": ["...", "..."]
}
```

### 3.5 Memory Mechanisms

- Reads `AgentInput.resume` (structured `Resume` Pydantic model).
- Appends `"ResumeCriticAgent: Analysed resume structure…"` to `context.decision_trace`.
- Adds `sharp_metadata` (ats_compatibility_checked, confidence_score).

### 3.6 Fallback Strategy

If `parse_and_validate()` raises, the exception propagates to the orchestrator which logs the error and returns an `AgentResponse` with `confidence_score=0.0`. The `_normalize_structural_assessment()` helper provides default values for missing fields.

### 3.7 Mock Key

`MOCK_RESUME_CRITIC_AGENT=true` in `.env` returns the `"ResumeCriticAgent"` entry from `mock_responses.json`, bypassing Gemini entirely.

---

## 4. ContentStrengthAgent

### 4.1 Purpose

Analyses resume content to identify key skills, achievements, and evidence of impact; generates faithful rephrasing suggestions with explainable confidence scores.

### 4.2 Reasoning Pattern

**Analytical with faithfulness constraint**. The agent evaluates each skill and achievement independently and applies a binary `faithful` flag to every suggestion. Suggestions that would require fabricating data are marked `faithful=false` and surfaced to the user for review.

### 4.3 Prompt Design

```
System:  Content Strength & Skills Reasoning Agent.
         Evidence Strength: HIGH | MEDIUM | LOW
         Faithful Transformation Rules:
           - NEVER invent new skills, metrics, or experiences.
           - If suggestion requires fabrication: faithful=false.
         Anti-jailbreak directive.
User:    "Resume data: <JSON>"
```

### 4.4 Output Schema (`ContentAnalysisReport`)

```json
{
  "skills": [{ "name", "category", "confidenceScore", "evidenceStrength", "evidence" }],
  "achievements": [{ "description", "impact", "quantifiable", "confidenceScore", "originalText" }],
  "suggestions": [{ "original", "suggested", "rationale", "faithful", "confidenceScore" }],
  "hallucinationRisk": 0.15,
  "summary": "..."
}
```

### 4.5 Confidence Calculation

Overall confidence is the **arithmetic mean** of per-category (skills, achievements, suggestions) average `confidenceScore` values. Categories with zero items are excluded from the mean.

### 4.6 Governance Integration

`SharpGovernanceService.audit()` runs a dedicated `_validate_content_strength_agent()` pass that:
- Reads `hallucinationRisk` from the content JSON.
- Counts `faithful=false` suggestions → flags `unfaithful_suggestions`.
- Counts `evidenceStrength=HIGH` skills → adds `high_evidence_skills_count`.

### 4.7 Memory Mechanisms

Decision trace entries record skill count, achievement count, suggestion count, and hallucination risk.

---

## 5. JobAlignmentAgent

### 5.1 Purpose

Semantically compares the candidate's resume against a job description to produce an alignment score, identify missing keywords, and provide role-fit analysis.

### 5.2 Reasoning Pattern

**Comparative analytical**. The agent receives both the resume JSON and the job description (appended to the prompt) and performs a structured comparison. A two-phase chain-of-thought approach is embedded in the system prompt: first, identify requirements from the JD; second, map each requirement to resume evidence.

### 5.3 Prompt Design

```
User: "<JSON resume>\nJD: <job description text>"
```

The orchestrator renders the input via `_render_input()` which explicitly appends `\nJD: …` only when intent is `ALIGNMENT`.

### 5.4 Output Schema

```json
{
  "alignmentScore": 0.82,
  "matchedKeywords": ["Python", "AWS", "CI/CD"],
  "missingKeywords": ["Kubernetes", "Terraform"],
  "roleFitSummary": "Strong match for backend role...",
  "recommendations": ["Add Terraform experience...", "..."]
}
```

### 5.5 Fallback Strategy

A regex-based JSON extraction (`_parse_json`) first strips markdown fences, then searches for `{…}` boundaries. If extraction fails, a minimal fallback object is returned.

---

## 6. InterviewCoachAgent

### 6.1 Purpose

Simulates role-specific interview scenarios, evaluates candidate responses, and provides structured coaching feedback.

### 6.2 Reasoning Pattern

**ReAct (Reason + Act)** with multi-turn conversation support. The agent receives the full `message_history` so it can:
1. **Reason**: analyse the candidate's previous answer.
2. **Act**: generate a follow-up question or provide detailed feedback.

The planning loop is driven by the conversation history — each user turn triggers a new `process()` call, and the agent re-reads the complete history to maintain context.

### 6.3 Prompt Design

```
System:  You are an expert Interview Coach. Given alignment gaps and the
         conversation so far, generate targeted questions and evaluate answers.
         Provide structured feedback: strengths, improvements, example answers.
User:    "Resume: <JSON>
          Message history: [{ role, text }, ...]"
```

### 6.4 Output Schema

```json
{
  "question": "Tell me about a time you led a team...",
  "feedback": {
    "strengths": ["Quantified the team size..."],
    "improvements": ["Could mention the business outcome..."],
    "exampleAnswer": "..."
  },
  "nextSteps": ["Practice STAR format...", "..."]
}
```

### 6.5 Memory Mechanism

`message_history` is the primary memory mechanism. The frontend sends the accumulated conversation with each request; the agent processes the full history on every turn. Long-term session state is persisted in `SessionContext.conversation_history`.

### 6.6 Audio Support

The agent optionally accepts `audio_data` (PCM → WAV converted via `audio_utils.pcm_to_wav`), allowing voice-based mock interviews.

---

## 7. OrchestrationAgent

### 7.1 Intent Routing

```python
INTENT_TO_AGENTS = {
    Intent.RESUME_CRITIC:    ["ResumeCriticAgent"],
    Intent.CONTENT_STRENGTH: ["ContentStrengthAgent"],
    Intent.ALIGNMENT:        ["JobAlignmentAgent"],
    Intent.INTERVIEW_COACH:  ["InterviewCoachAgent"],
}
```

Each intent maps to an ordered list of agents. Future extensions (e.g., running ResumeCritic before JobAlignment) require only updating this map.

### 7.2 LangGraph Planning Loop

```
StateGraph
  entry_point: run_agent
  conditional_edge: index < len(sequence) → continue | end
```

Each iteration:
1. Pop `agent_sequence[index]`, look up agent.
2. Render prompt from `AgentInput`.
3. Call `agent.process()`.
4. Governance audit.
5. Append to `context.decision_trace` and `state.artifacts`.
6. Increment index.

### 7.3 Resume Normalisation

The orchestrator normalises resume input before the agent pipeline runs:
- **resumeData** (structured JSON): used directly.
- **resumeFile** (base64 PDF): routed through `ExtractorAgent` → parsed to `Resume`.
- **Neither**: immediate failure response.

### 7.4 Inter-Agent Communication Protocol

Agents do **not** call each other directly. All communication flows through the shared `OrchestrationState`:

```
OrchestrationState
├── input: AgentInput       (immutable per orchestration run)
├── context: SessionContext  (mutated by each agent via _update_context)
├── agent_sequence: List[str]
├── artifacts: List[AnalysisArtifact]
├── index: int
└── response: Optional[AgentResponse]
```

`context.shared_memory` accumulates agent outputs across the pipeline. `context.decision_trace` provides a breadcrumb audit trail.

---

## 8. Prompt Patterns & Anti-Jailbreak

All agents append:
1. **`RESUME_SCHEMA`** — informs the LLM of the expected input schema.
2. **`ANTI_JAILBREAK_DIRECTIVE`** — prevents role-play, instruction override, and schema bypass attempts.

System prompts explicitly prohibit:
- Markdown code fences in output.
- Null values (use empty strings/arrays instead).
- Fabricated metrics or experiences.

---

## 9. Autonomy Model

| Aspect | Detail |
|--------|--------|
| **Decision autonomy** | Low — each agent performs a single analytical task; no autonomous tool calls or web search |
| **Memory autonomy** | Medium — agents read from and write to shared `SessionContext`; state persists across HTTP calls |
| **Action autonomy** | None — agents produce text recommendations; all changes require explicit user approval (HITL) |
| **Planning autonomy** | Low — agent sequence is deterministically set by intent; no dynamic re-planning in current release |
