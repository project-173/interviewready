# Bias Detection & Transparency - Quick Reference

## What Changed?

### 1️⃣ **Bias Categories Expanded from 6 → 11**

```python
# OLD (6 categories)
BIAS_PATTERNS = {
    "age", "gender", "nationality", "disability", 
    "family_status", "religion"
}

# NEW (11 categories) 
BIAS_PATTERNS = {
    "age", "gender", "nationality", "disability",
    "family_status", "religion",
    "socioeconomic_status",      # ← NEW
    "sexual_orientation",        # ← NEW
    "genetic_information",       # ← NEW
    "appearance",                # ← NEW
    "veteran_status"             # ← NEW
}
```

### 2️⃣ **User-Facing Transparency Fields**

Every API response now includes:

```json
{
  "payload": "...",
  "confidence_score": 0.85,
  "confidence_explanation": "High confidence: Well-supported by information.",
  "reasoning": "Decision based on answer structure and job alignment.",
  "improvement_suggestions": ["Add specific examples with metrics"],
  "bias_flags": ["gender", "age"],
  "bias_severity": "warning",
  "bias_description": "Job description contains gendered language and age-related terms...",
  "governance_audit_status": "flagged",
  "governance_flags": ["bias_detected", "requires_human_review"],
  "answer_score": 78,
  "can_proceed": true,
  "next_challenge": "Focus on quantified impact"
}
```

### 3️⃣ **Transparency Component**

Frontend now displays user-friendly transparency:

```
┌─────────────────────────────────────────────┐
│ ✓ AI Confidence: 85%                        │
│   High confidence: Well-supported by info   │
├─────────────────────────────────────────────┤
│ 📊 Answer Score: 78/100                      │
│   Ready to Proceed: ✓ Yes                   │
├─────────────────────────────────────────────┤
│ ⚠ Fairness & Bias Alert                     │
│   Detected: gender, age                     │
│   Recommendation: Remove gendered language  │
├─────────────────────────────────────────────┤
│ 💡 Suggestions for Improvement              │
│   • Add specific examples with metrics      │
│   • Quantify business impact                │
└─────────────────────────────────────────────┘
```

## How It Works

### Backend Flow

```
Agent Detection
  ├─ InterviewCoachAgent._detect_bias_flags(text)
  │   └─ Returns List[str] of detected categories
  │
Agent Response Creation
  ├─ AgentResponse(
  │    bias_flags=["age", "gender"],
  │    bias_severity="warning",
  │    confidence_score=0.85,
  │    confidence_explanation="...",
  │    improvement_suggestions=[...],
  │    governance_flags=["bias_detected"]
  │  )
  │
API Transformation
  ├─ enrich_agent_response_for_user(response)
  │   └─ Auto-generates explanations if missing
  │
  ├─ agent_response_to_api(response)
  │   └─ Transforms to ChatApiResponse with all fields
  │
HTTP Response
  └─ ChatApiResponse with transparency fields
```

### Detection Example

```python
from app.agents.interview_coach import InterviewCoachAgent

agent = InterviewCoachAgent(gemini_service)

# Detect bias in job description
jd = "We need a young, energetic female with no childcare obligations"
bias_flags = agent._detect_bias_flags(jd)

print(bias_flags)
# Output: ["age", "gender", "family_status"]
```

## API Usage

### Request (unchanged)
```python
POST /api/v1/chat
{
  "intent": "ALIGNMENT",
  "jobDescription": "Senior Python Engineer...",
  "resumeData": {...}
}
```

### Response (enhanced with transparency)
```python
{
  "agent": "JobAlignmentAgent",
  "payload": {
    "skillsMatch": ["Python", "AWS"],
    "missingSkills": ["Kubernetes"],
    "summary": "..."
  },
  # NEW TRANSPARENCY FIELDS
  "confidence_score": 0.75,
  "confidence_explanation": "Moderate confidence based on 2 matches, 1 missing skill",
  "bias_flags": ["gender"],
  "bias_severity": "info",
  "bias_description": "Detected feminine gendered language. Consider using gender-neutral terms.",
  "improvement_suggestions": ["Use inclusive language in job descriptions"],
  "governance_audit_status": "flagged",
  "governance_flags": ["bias_detected"],
  "requires_human_review": true
}
```

## Frontend Integration

### Types (frontend/types.ts)

Already compatible! InterviewMessage type already has:
```typescript
interface InterviewMessage {
  confidence_score?: number;
  reasoning?: string;
  decision_trace?: string[];
  improvement_suggestion?: string;
  answer_score?: number;
  can_proceed?: boolean;
  bias_warnings?: string[];
  governance_flags?: string[];
  requires_human_review?: boolean;
}
```

### Display Component

```tsx
<TransparencyMetadata message={agentMessage} />
```

The component automatically displays all available transparency fields with:
- ✅ Color-coded severity
- ✅ Actionable recommendations
- ✅ Step-by-step reasoning
- ✅ Governance notices

## Testing

Run all bias detection tests:
```bash
cd backend
python -m pytest tests/test_bias_detection_transparency.py -v
```

Run specific test:
```bash
python -m pytest tests/test_bias_detection_transparency.py::TestBiasDetectionExpansion::test_interview_coach_age_bias_detection -v
```

## Compliance Alignment

### ✅ IMDA Model AI Governance Framework

| Pillar | Implementation |
|--------|-----------------|
| **Internal Governance** | 11 bias categories, structured metadata, CI enforcement |
| **Human Involvement** | Bias flags trigger review recommendations, advisory (not autonomous) |
| **Operations** | Multi-layer scanning, PII redaction, governance audit |
| **Communication** | Candidates/employers see confidence, reasoning, suggestions |

### ✅ Responsible AI Principles

- **Fairness**: 11-category bias detection + severity scoring
- **Explainability**: Confidence scores, decision traces, reasoning
- **Transparency**: User-facing explanations + governance flags
- **Accountability**: Decision audit trail in Langfuse

## Langfuse Integration

Bias information automatically logged:

```python
langfuse.update_current_span(
    output={
        "confidence_score": 0.85,
        "bias_flags": ["gender", "age"],
        "bias_flags_count": 2,
        "governance_flags": ["bias_detected", "requires_human_review"],
        "governance_audit_status": "flagged"
    }
)
```

Query Langfuse cloud for bias trends:
```sql
SELECT 
  model, 
  COUNT(*) as total_responses,
  SUM(CASE WHEN 'bias_detected' IN governance_flags THEN 1 ELSE 0 END) as bias_flagged
FROM observations
WHERE type = 'agent'
GROUP BY model
```

## Common Questions

**Q: How do users see transparency info?**
A: Via the TransparencyMetadata component which displays confidence, reasoning, bias detection, and suggestions automatically.

**Q: What if I want to add more bias categories?**
A: Add to `BIAS_PATTERNS` dict in agent and expand recommendations in `build_bias_recommendation()`.

**Q: How strict is bias detection?**
A: Pattern-based heuristics, intentionally inclusive to avoid false negatives. Human review recommended for flagged items.

**Q: Do users see all governance flags?**
A: Only bias-related and human-review flags are shown to users. Internal SHARP metadata available for advanced users.

**Q: Can employers disable bias detection?**
A: Currently on by default. Could add feature flag if needed - file issue.

## Next Steps

- [ ] Run full test suite to verify all components
- [ ] Deploy to staging environment
- [ ] Monitor bias detection hits in Langfuse
- [ ] Gather user feedback on transparency UX
- [ ] Consider ML-based bias detection as v2
