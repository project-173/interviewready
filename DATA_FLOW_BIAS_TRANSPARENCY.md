# Complete Data Flow: Bias Detection → User Transparency

## End-to-End Example

### 1. User Submission
```
Candidate submits interview response to:
  Job Description: "We're seeking young, energetic rockstars with no family obligations"
  Resume: "Python, AWS, 10 years experience"
```

### 2. Backend Processing

#### InterviewCoachAgent.process()
```python
# Detect bias in JD
bias_flags = self._detect_bias_flags(job_desc)
# Result: ["age", "gender", "family_status"]

# Determine severity
if len(bias_flags) > 3:
    bias_severity = "critical"
elif len(bias_flags) > 2:
    bias_severity = "warning"  # ← This case
else:
    bias_severity = "info"

# Build suggestions
improvement_suggestions = [
    "Job description contains biased language (age, gender, family_status). "
    "Consider using inclusive alternatives."
]

# Create response
response = AgentResponse(
    agent_name="InterviewCoachAgent",
    content="...",
    confidence_score=0.85,
    bias_flags=["age", "gender", "family_status"],
    bias_severity="warning",
    governance_audit_status="flagged",
    governance_flags=["bias_detected", "requires_human_review"],
    improvement_suggestions=improvement_suggestions,
    # ... other fields
)
```

### 3. API Enrichment

#### enrich_agent_response_for_user()
```python
# Auto-generate explanations if not present
if not response.confidence_explanation:
    response.confidence_explanation = (
        "High confidence: Response is well-supported by the provided information."
    )

if not response.bias_description:
    response.bias_description = (
        "Potential bias detected in 3 categories: age, gender, family_status. "
        "Please review the job description for inclusive language."
    )
```

### 4. API Response Transformation

#### agent_response_to_api()
```python
# Create user-facing response
api_response = ChatApiResponse(
    agent="InterviewCoachAgent",
    payload=response.content,
    confidence_score=0.85,
    confidence_explanation="High confidence: Response is well-supported...",
    reasoning="Generated interview coaching based on resume-job alignment...",
    improvement_suggestions=[
        "Job description contains biased language (age, gender, family_status)..."
    ],
    bias_flags=["age", "gender", "family_status"],
    bias_severity="warning",
    bias_description="Potential bias detected in 3 categories...",
    governance_audit_status="flagged",
    governance_flags=["bias_detected", "requires_human_review"],
    requires_human_review=True,
    answer_score=82,
    can_proceed=True,
    next_challenge="Focus on quantifying business impact"
)
```

### 5. Langfuse Logging

```python
# Logged to Langfuse with full metadata
langfuse.update_current_span(
    output={
        "success": True,
        "agent": "InterviewCoachAgent",
        "response_length": 450,
        "confidence_score": 0.85,
        "bias_flags_count": 3,
        "governance_flags": ["bias_detected", "requires_human_review"],
        "governance_audit_status": "flagged"
    }
)

# Creates observable trace:
# trace_id: 12345
#   span: chat_endpoint
#     ├─ input: ChatRequest
#     ├─ output: ChatApiResponse
#     │   ├─ confidence_score: 0.85
#     │   ├─ bias_flags: [age, gender, family_status]
#     │   └─ governance_flags: [bias_detected]
#     └─ latency: 234ms
```

### 6. Frontend Display

#### HTTP Response
```json
{
  "agent": "InterviewCoachAgent",
  "payload": {
    "current_question_number": 2,
    "question": "Tell me about a time you overcame...",
    "feedback": "Great example! More specific metrics would strengthen...",
    "answer_score": 82,
    "can_proceed": true
  },
  "confidence_score": 0.85,
  "confidence_explanation": "High confidence: Response is well-supported by provided information.",
  "reasoning": "Generated interview coaching based on resume-job alignment and answer-quality heuristics.",
  "improvement_suggestions": [
    "Add quantity or percentage to your impact statements",
    "Mention business outcome, not just technical achievement"
  ],
  "bias_flags": ["age", "gender", "family_status"],
  "bias_severity": "warning",
  "bias_description": "Potential bias detected in 3 categories: age, gender, family_status. Please review the job description for inclusive language.",
  "governance_audit_status": "flagged",
  "governance_flags": ["bias_detected", "requires_human_review"],
  "requires_human_review": true,
  "answer_score": 82,
  "can_proceed": true,
  "next_challenge": "Focus on quantifying business impact"
}
```

#### React Component Receives Data
```tsx
<WorkflowSteps>
  <ChatMessage role="agent" text="Great example!..." />
  <TransparencyMetadata
    message={{
      role: "agent",
      text: "Great example!...",
      confidence_score: 0.85,
      reasoning: "Generated interview coaching...",
      improvement_suggestion: "Add metrics...",
      answer_score: 82,
      can_proceed: true,
      bias_warnings: ["age", "gender", "family_status"],
      governance_flags: ["bias_detected", "requires_human_review"],
      requires_human_review: true
    }}
  />
</WorkflowSteps>
```

#### What User Sees
```
┌──────────────────────────────────────────────────────────┐
│ Assistant: Great example! More specific metrics would... │
├──────────────────────────────────────────────────────────┤
│ 📊 CONFIDENCE & SCORING                                   │
│   Model Confidence:  ████████████████░░ 85%              │
│   Answer Score:      82/100                              │
│   Ready to Proceed:  ✓ Yes                               │
├──────────────────────────────────────────────────────────┤
│ 🧠 DECISION REASONING                                     │
│   Generated interview coaching based on resume-job       │
│   alignment and answer-quality heuristics.               │
│                                                          │
│   Evaluation Steps:                                      │
│   • Analyzed STAR methodology usage                      │
│   • Evaluated business impact clarity                    │
│   • Assessed relevance to job role                       │
├──────────────────────────────────────────────────────────┤
│ ⚠ FAIRNESS & BIAS ALERT                                 │
│   Potential bias signals detected in job description:    │
│   [age] [gender] [family_status]                         │
│                                                          │
│   These signals have been flagged for review to help     │
│   ensure inclusive hiring practices aligned with         │
│   responsible AI and anti-discrimination principles.     │
├──────────────────────────────────────────────────────────┤
│ 💡 SUGGESTION FOR IMPROVEMENT                            │
│   • Add quantity or percentage to impact statements      │
│   • Mention business outcome, not just achievement       │
│   • Use STAR format for structure                        │
├──────────────────────────────────────────────────────────┤
│ 🔒 GOVERNANCE NOTICE                                     │
│   Flags: bias_detected, requires_human_review            │
│   Status: ⚠ Flagged                                      │
│                                                          │
│   ℹ Human review recommended                             │
└──────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User Input                               │
│  Resume + Job Description + Interview Answer               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│            InterviewCoachAgent.process()                    │
│  ├─ _detect_bias_flags(job_desc)                           │
│  │   └─ Returns: ["age", "gender", "family_status"]        │
│  ├─ Determine severity: "warning"                          │
│  ├─ Build suggestions                                      │
│  └─ Create AgentResponse with transparency fields          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         enrich_agent_response_for_user()                    │
│  ├─ Generate confidence_explanation                        │
│  ├─ Generate bias_description                              │
│  └─ Ensure all explanations are user-friendly              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│          agent_response_to_api()                            │
│  ├─ Extract payload from internal response                 │
│  ├─ Map all transparency fields to API response            │
│  ├─ Determine requires_human_review flag                   │
│  └─ Create ChatApiResponse                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         chat_endpoint() HTTP Response                       │
│  ├─ confidence_score, confidence_explanation               │
│  ├─ bias_flags, bias_severity, bias_description            │
│  ├─ governance_audit_status, governance_flags              │
│  ├─ improvement_suggestions                                │
│  ├─ answer_score, can_proceed, next_challenge              │
│  └─ requires_human_review                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
    ┌────────┐    ┌──────────┐   ┌─────────┐
    │Frontend│    │ Langfuse │   │Database │
    │Display │    │  Logging │   │Audit    │
    └────────┘    └──────────┘   └─────────┘
        │              │              │
        ▼              ▼              ▼
    Show User      Log Trace      Store for
    Transparency   with Bias      Compliance
    Info & Bias    Metadata       Reports
    Alerts         
```

## Key Transformation Points

### Point 1: Detection
```
Raw JD Text
    ↓
Regex Pattern Matching (11 categories)
    ↓
List of Bias Categories: ["age", "gender", "family_status"]
```

### Point 2: Enrichment
```
Raw AgentResponse
    ↓
Auto-generate Explanations
    ↓
Enhanced AgentResponse with user-friendly text
```

### Point 3: Transformation
```
Enhanced AgentResponse (internal)
    ↓
Extract PublicResponse Fields
    ↓
ChatApiResponse (external API contract)
```

### Point 4: Presentation
```
ChatApiResponse JSON
    ↓
Frontend Type System
    ↓
React Component Logic
    ↓
User-Facing Display with Color Coding
```

## Example Values at Each Stage

### Stage 1: Detection
```
Input: "We need energetic, young females with no kids"
Output: {
  "age": true,
  "gender": true,
  "family_status": true
}
```

### Stage 2: Enrichment
```
Input: AgentResponse(bias_flags=["age", "gender", "family_status"])
Output: AgentResponse(
  bias_flags=["age", "gender", "family_status"],
  bias_severity="warning",
  bias_description="Potential bias in 3 categories..."
)
```

### Stage 3: Transformation
```
Input: Internal AgentResponse
Output: ChatApiResponse(
  bias_flags=["age", "gender", "family_status"],
  bias_severity="warning",
  bias_description="...",
  requires_human_review=true
)
```

### Stage 4: Display
```
CSS Classes: border-amber-200 bg-amber-50 text-amber-800
Icon: ⚠
Title: Fairness & Bias Alert
Content: Visual chips for each category
Action: Link to recommendations
```

## Performance Characteristics

| Component | Latency | Impact |
|-----------|---------|--------|
| Bias detection (regex) | 1-5ms | Negligible |
| Enrichment (string generation) | 2-8ms | Negligible |
| API transformation | <1ms | None (memory only) |
| Frontend rendering | 50-200ms | User perceivable |
| Total E2E | ~60-250ms | Already included in response time |
| Langfuse logging | Async | No blocking |

## Compliance Audit Trail

Every response includes:
- ✅ **What**: bias_flags, governance_flags, confidence_score
- ✅ **Why**: reasoning, confidence_explanation, bias_description
- ✅ **When**: timestamp in Langfuse
- ✅ **Who**: user_id, session_id in Langfuse
- ✅ **Decision**: answer_score, can_proceed, governance_audit_status
- ✅ **Impact**: improvement_suggestions, next_challenge

Query in Langfuse:
```sql
SELECT 
  trace_id,
  user_id,
  timestamp,
  output->>'bias_flags' as bias_flags,
  output->>'governance_audit_status' as status,
  output->>'confidence_score' as confidence
FROM observations
WHERE environment = 'production'
  AND output->>'governance_audit_status' = 'flagged'
ORDER BY timestamp DESC
```
