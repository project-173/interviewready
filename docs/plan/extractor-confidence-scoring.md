# Extractor Agent Dynamic Confidence Scoring

## Overview

Replace the hardcoded `CONFIDENCE_SCORE = 0.95` in `ExtractorAgent` with a dynamic scoring mechanism to enable HITL (Human-In-The-Loop) when extraction quality is low.

## Current State

- `backend/app/agents/extractor.py:27` - `CONFIDENCE_SCORE = 0.95` (hardcoded)
- Used in `ResumeDocument.parse_confidence` and `AgentResponse.confidence_score`

## Implementation Plan

### Phase 1: Enhanced Confidence Score Calculation

**File:** `backend/app/agents/extractor.py`

Add a `_calculate_confidence_score()` method that evaluates:

| Factor | Weight | Description |
|--------|--------|-------------|
| Field-Weighted Completeness | -0.4 | Required fields weighted higher than optional |
| LLM Self-Reported Uncertainty | -0.2 | Extractor flags uncertain fields (validated empirically) |
| Source Quality Indicators | -0.2 | Parser warnings, capped at -0.3 total |
| Structural Completeness | -0.2 | Expected resume sections present |

**Field Weighting:**
- Required fields (personal_info, work_experience): 2.0x weight
- Important fields (education, skills): 1.5x weight  
- Optional fields (awards, certifications): 1.0x weight

**Enhanced LLM Prompt:**
```
Extract resume data into the specified JSON format. After extracting all resume data, add a "_confidence" key with this structure:
{
    "_confidence": {
        "overall": "HIGH" | "MEDIUM" | "LOW",
        "low_confidence_fields": ["work[0].startDate", "education[0].url"],
        "reasons": ["Employment dates unclear", "No institution URL in source"]
    }
}

Flag a field as low confidence if:
- The value was inferred, not explicitly stated
- The source text was ambiguous or contradictory  
- You had to guess a format (especially dates)

Example low_confidence_fields format:
- "personal_info.phone" for top-level fields
- "work[0].startDate" for array items
- "education[1].gpa" for nested array fields
```

**Implementation in ExtractorAgent:**
```python
def _generate_llm_response(self, text: str, context: SessionContext) -> tuple[Resume, float, list[str]]:
    # Get LLM response with confidence flags (synchronous to match real code)
    raw_result = self.call_gemini(text, context)
    
    # Parse JSON response
    parsed_result = parse_json_object(raw_result)
    
    # Extract confidence before validation strips it
    confidence_map = parsed_result.pop("_confidence", {})
    
    # Validate resume data against schema (returns Resume, not dict)
    validated_result, validation_errors = self._validate_data(parsed_result, text)
    
    # Handle validation errors explicitly before scoring
    self._handle_validation_errors(validation_errors, validated_result)
    
    # Calculate confidence score using extracted data
    confidence_score = self._calculate_confidence_score(
        resume=validated_result,
        confidence_map=confidence_map,
        source_text=text,
        validation_errors=validation_errors
    )
    
    low_confidence_fields = confidence_map.get("low_confidence_fields", [])
    return validated_result, confidence_score, low_confidence_fields
```

**Modified process() method (partial diff):**
```python
def process(self, input_data: AgentInput | str | bytes, context: SessionContext) -> AgentResponse:
    # ... existing PDF parsing, base64 decoding, mock routing, metadata assembly ...
    
    # REPLACE THIS SECTION:
    # OLD:
    # resume = self._extract_resume_with_llm(extracted_text, context)
    # confidence_score = CONFIDENCE_SCORE  # hardcoded 0.95
    # 
    # NEW:
    resume, confidence_score, low_confidence_fields = self._generate_llm_response(extracted_text, context)
    
    # ... rest of existing process() method continues unchanged ...
    
    return AgentResponse(
        data=resume,
        confidence_score=confidence_score,
        low_confidence_fields=low_confidence_fields,
        needs_review=confidence_score < EXTRACTOR_AUTO_PROCEED_THRESHOLD
    )
```

**Note:** This is a partial modification to the existing process() method. All other functionality (PDF parsing, mock routing, Langfuse observation, metadata handling) remains unchanged.

**Confidence Score Calculation:**
```python
def _calculate_confidence_score(self, resume: Resume, confidence_map: dict, source_text: str, validation_errors: list) -> float:
    # Extract confidence data from LLM
    low_confidence_fields = confidence_map.get("low_confidence_fields", [])
    
    # Calculate field counts
    total_fields = self._count_total_fields(resume)
    low_confidence_count = len(low_confidence_fields)
    
    # Start from 1.0 and apply penalties (no double-counting)
    base_score = 1.0
    
    # Apply scoring formula
    completeness_penalty = (1.0 - self._weighted_completeness_ratio(resume)) * 0.4
    uncertainty_penalty = (low_confidence_count / max(total_fields, 1)) * 0.2
    quality_penalty = min(self._count_parser_warnings(source_text) * 0.1, 0.3)
    structure_penalty = min(self._count_missing_sections(resume) * 0.2, 0.2)
    validation_penalty = min(len(validation_errors) * 0.05, 0.1)  # Bounded validation penalty
    
    # Combine with uncertainty weight (starts at 0.0 until validation)
    uncertainty_weight = EXTRACTOR_UNCERTAINTY_WEIGHT if EXTRACTOR_UNCERTAINTY_VALIDATION_COMPLETE else 0.0
    final_score = max(0.0, base_score - completeness_penalty - (uncertainty_penalty * uncertainty_weight) - quality_penalty - structure_penalty - validation_penalty)
    
    return final_score
```

**Scoring Formula:**
```
base_score = 1.0  # Start from perfect score, apply penalties
completeness_penalty = (1.0 - weighted_completeness_ratio) * 0.4
uncertainty_penalty = (low_confidence_fields / total_fields) * 0.2
quality_penalty = min(parser_warnings * 0.1, 0.3)  # Capped at -0.3
structure_penalty = min(missing_expected_sections * 0.2, 0.2)  # Capped at -0.2
validation_penalty = min(len(validation_errors) * 0.05, 0.1)  # Bounded validation penalty

# Apply uncertainty weight only after validation complete
uncertainty_weight = EXTRACTOR_UNCERTAINTY_WEIGHT if EXTRACTOR_UNCERTAINTY_VALIDATION_COMPLETE else 0.0
score = max(0.0, base_score - completeness_penalty - (uncertainty_penalty * uncertainty_weight) - quality_penalty - structure_penalty - validation_penalty)

**⚠️ LLM Uncertainty Validation Required:**
Before committing to the 0.2 weight, run a validation study:
- Extract 100 resumes with self-reported confidence levels
- Have humans verify accuracy of HIGH/MEDIUM/LOW fields
- Correlate self-ratings with actual correction rates
- Adjust weight based on empirical correlation (target: ≥0.7 correlation)

**Implementation Approach:**
- Ship with `EXTRACTOR_UNCERTAINTY_WEIGHT = 0.0` (disabled)
- Run validation study in parallel with production deployment
- Enable uncertainty scoring by setting `EXTRACTOR_UNCERTAINTY_WEIGHT = 0.2` and `EXTRACTOR_UNCERTAINTY_VALIDATION_COMPLETE = True` after validation passes
```

### Phase 2: Validation Decoupling

**Separate validation from confidence scoring:**

1. **Pre-scoring Validation:** Handle deterministic errors explicitly
   - Fix URL formats automatically
   - Flag invalid dates for user correction
   - Strip malformed data fields
   
2. **Post-validation Confidence:** Score only the quality of extracted data, not parsing errors

**Refactor _validate_data method:**
```python
def _validate_data(self, data: dict, source_text: str) -> tuple[Resume, list[str]]:
    """Validate resume data and return (Resume, errors).
    
    Returns:
        tuple[Resume, list[str]]: (validated Resume object, list of validation error descriptions)
    """
    errors = []
    cleaned_data = data.copy()
    source_lower = source_text.lower()
    
    # Validate nested URLs and dates in work entries
    if "work" in cleaned_data:
        for i, work_item in enumerate(cleaned_data["work"]):
            if "url" in work_item:
                url = work_item["url"]
                if not self._is_valid_url(url):
                    errors.append(f"Invalid URL in work[{i}]: {url}")
                    work_item["url"] = ""  # Strip invalid URL
                elif self._is_full_url(url) and url.lower() not in source_lower:
                    errors.append(f"Hallucinated URL in work[{i}]: {url}")
                    work_item["url"] = ""  # Strip hallucinated URL
            if "startDate" in work_item and not self._is_valid_date(work_item["startDate"]):
                errors.append(f"Invalid startDate in work[{i}]: {work_item['startDate']}")
            if "endDate" in work_item and not self._is_valid_date(work_item["endDate"]):
                errors.append(f"Invalid endDate in work[{i}]: {work_item['endDate']}")
    
    # Validate nested URLs and dates in education entries
    if "education" in cleaned_data:
        for i, edu_item in enumerate(cleaned_data["education"]):
            if "url" in edu_item:
                url = edu_item["url"]
                if not self._is_valid_url(url):
                    errors.append(f"Invalid URL in education[{i}]: {url}")
                    edu_item["url"] = ""  # Strip invalid URL
                elif self._is_full_url(url) and url.lower() not in source_lower:
                    errors.append(f"Hallucinated URL in education[{i}]: {url}")
                    edu_item["url"] = ""  # Strip hallucinated URL
            if "startDate" in edu_item and not self._is_valid_date(edu_item["startDate"]):
                errors.append(f"Invalid startDate in education[{i}]: {edu_item['startDate']}")
            if "endDate" in edu_item and not self._is_valid_date(edu_item["endDate"]):
                errors.append(f"Invalid endDate in education[{i}]: {edu_item['endDate']}")
    
    # Validate nested URLs and dates in projects entries
    if "projects" in cleaned_data:
        for i, project_item in enumerate(cleaned_data["projects"]):
            if "url" in project_item:
                url = project_item["url"]
                if not self._is_valid_url(url):
                    errors.append(f"Invalid URL in projects[{i}]: {url}")
                    project_item["url"] = ""  # Strip invalid URL
                elif self._is_full_url(url) and url.lower() not in source_lower:
                    errors.append(f"Hallucinated URL in projects[{i}]: {url}")
                    project_item["url"] = ""  # Strip hallucinated URL
            if "startDate" in project_item and not self._is_valid_date(project_item["startDate"]):
                errors.append(f"Invalid startDate in projects[{i}]: {project_item['startDate']}")
            if "endDate" in project_item and not self._is_valid_date(project_item["endDate"]):
                errors.append(f"Invalid endDate in projects[{i}]: {project_item['endDate']}")
    
    # Validate nested URLs in certificates entries
    if "certificates" in cleaned_data:
        for i, cert_item in enumerate(cleaned_data["certificates"]):
            if "url" in cert_item:
                url = cert_item["url"]
                if not self._is_valid_url(url):
                    errors.append(f"Invalid URL in certificates[{i}]: {url}")
                    cert_item["url"] = ""  # Strip invalid URL
                elif self._is_full_url(url) and url.lower() not in source_lower:
                    errors.append(f"Hallucinated URL in certificates[{i}]: {url}")
                    cert_item["url"] = ""  # Strip hallucinated URL
            if "date" in cert_item and not self._is_valid_date(cert_item["date"]):
                errors.append(f"Invalid date in certificates[{i}]: {cert_item['date']}")
    
    # Schema validation
    try:
        validated = Resume.model_validate(cleaned_data)
        return validated, errors
    except ValidationError as e:
        errors.extend([f"Schema error: {err['msg']}" for err in e.errors()])
        # Return cleaned data as Resume if possible, or raise for critical errors
        try:
            fallback = Resume.model_validate(cleaned_data, strict=False)
            return fallback, errors
        except Exception:
            raise ValueError(f"Critical validation errors: {errors}")
```

**Handle validation errors explicitly:**
```python
def _handle_validation_errors(self, errors: list[str], resume_data: Resume) -> None:
    """Log validation errors without short-circuiting confidence scoring."""
    if errors:
        logger.warning(f"Validation errors handled: {errors}")
        # Could also add metrics or alerts here for critical errors
```

### Phase 3: Configuration & Thresholds

**File:** `backend/app/core/config.py`

```python
# HITL Configuration
EXTRACTOR_HITL_THRESHOLD = 0.6      # Below this triggers HITL
EXTRACTOR_AUTO_PROCEED_THRESHOLD = 0.9  # Above this auto-proceeds
EXTRACTOR_HITL_TIMEOUT_MINUTES = 30    # Max wait time for human input
EXTRACTOR_HITL_FALLBACK = "proceed"    # Options: "proceed", "fail", "queue"

# ⚠️ Timeout Fallback Implications:
# "proceed" = Continue with original low-confidence extraction
# "fail" = Stop pipeline, require manual intervention
# "queue" = Re-queue for later human review
# All timeouts log as distinct event: hitl_timeout_proceeded/failed/queued

# Field Weights for Scoring
EXTRACTOR_FIELD_WEIGHTS = {
    "required": 2.0,
    "important": 1.5, 
    "optional": 1.0
}

# LLM Uncertainty Validation Gate
EXTRACTOR_UNCERTAINTY_WEIGHT = 0.0  # Start disabled until validation passes
EXTRACTOR_UNCERTAINTY_VALIDATION_COMPLETE = False  # Set to True after validation study
```

### Phase 4: Orchestration Layer Integration

**File:** `backend/app/orchestration/orchestration_agent.py`

**Decision Logic:**
- **> AUTO_PROCEED_THRESHOLD**: Continue normal flow
- **HITL_THRESHOLD ≤ score ≤ AUTO_PROCEED_THRESHOLD**: Mark as "needs_review", continue with flag
- **< HITL_THRESHOLD**: Route to HITL flow

**Review Flag Handling:**
- Add `needs_review: bool` to `AgentResponse`
- Frontend displays subtle review indicator for flagged extractions
- Users can voluntarily review but workflow continues

### Phase 5: HITL Flow Implementation

#### 5.1 Session Storage Architecture

**Storage Pattern:** Redis + Database
- **Redis:** Active session state (TTL: 2x HITL_TIMEOUT_MINUTES)
- **Database:** Audit trail and session recovery (permanent)

**HITLSession Model:**
```python
class HITLSession(BaseModel):
    session_id: str
    original_extraction: ResumeDocument
    confidence_score: float
    low_confidence_fields: List[str]
    status: "pending" | "completed" | "timeout" | "cancelled"
    created_at: datetime
    timeout_at: datetime
    corrected_data: Optional[ResumeDocument] = None
    timeout_action: Optional[str] = None  # "proceeded"|"failed"|"queued"
```

**Async Flow:**
1. **Pause Point:** Orchestration stores session in Redis + DB, returns `HITL_REQUIRED` response
2. **User Notification:** WebSocket/polling notifies frontend of pending review
3. **Correction Interface:** Users edit only low-confidence fields (or full review)
4. **Resume Pipeline:** Corrections bypass extraction, go directly to validation
5. **Timeout Handling:** Configurable fallback with distinct logging for audit trail

#### 5.2 User Experience Design

**HITL Interface Components:**
- **Field-Level Confidence Indicators:** Color-coded confidence levels
- **Smart Defaults:** Pre-fill with original extraction, highlight uncertain fields
- **Quick Actions:** "Accept All", "Fix Only Low Confidence", "Full Review"
- **Progress Tracking:** Show remaining HITL items in queue

**Response Options:**
- Submit corrections → Resume pipeline with corrected data
- Skip → Continue with original extraction  
- Request full review → Expand to all fields

#### 5.3 API Endpoints

```python
# HITL Session Management
POST /api/v1/hitl/sessions/{session_id}/submit
GET  /api/v1/hitl/sessions/{session_id}
POST /api/v1/hitl/sessions/{session_id}/skip

# WebSocket for real-time notifications
WS   /api/v1/hitl/notifications/{user_id}
```

### Phase 6: Observability & Feedback Loop

#### 6.1 HITL Analytics Logging

**Log Structure:**
```python
{
  "event": "hitl_triggered",
  "session_id": "uuid",
  "confidence_score": 0.42,
  "trigger_reasons": ["low_completeness", "high_uncertainty"],
  "field_count": {"total": 15, "low_confidence": 8},
  "user_id": "user_123"
}

{
  "event": "hitl_completed", 
  "session_id": "uuid",
  "corrections_made": 5,
  "fields_corrected": ["company_name", "employment_dates"],
  "time_to_complete_minutes": 4.2,
  "final_confidence_score": 0.89
}
```

#### 6.2 Calibration Dashboard (Phase 2 Scope)

**Phase 1:** Basic logging only (as specified above)
**Phase 2:** Full calibration dashboard with:
- HITL trigger rate by score ranges
- Correction patterns by field type
- Time-to-complete distributions
- User satisfaction scores
- Automated threshold suggestions

**Rationale:** Dashboard is a significant project that can be developed after core HITL functionality is proven.

## Updated Acceptance Criteria

1. **Enhanced Scoring:** Confidence score uses field-weighted completeness and LLM self-reported uncertainty (not just heuristics)
2. **Validation Separation:** Validation errors are handled explicitly before confidence scoring (not double-penalized)
3. **Actionable Thresholds:** Three-tier system with clear actions for each band
4. **Async HITL Flow:** Complete pause/resume pattern with timeout handling and user notification
5. **Observability:** Comprehensive logging of HITL triggers and corrections for threshold calibration
6. **Configuration:** All thresholds and weights externalized to config

## Implementation Priority

**Critical Path (Corrected Dependencies):**
1. Phase 1: Enhanced scoring with LLM uncertainty
2. Phase 2: Validation decoupling  
3. Phase 3: Configuration externalization
4. Phase 4: Orchestration integration (prerequisite for Phase 5)
5. Phase 5: Async HITL architecture (requires routing from Phase 4)
6. Phase 6: Observability and feedback

**Risk Mitigation:**
- Start with conservative thresholds (0.6 HITL, 0.9 auto-proceed)
- Implement timeout fallback to "proceed" to avoid pipeline stalls
- Add comprehensive logging from day 1 for threshold calibration
- Validate LLM uncertainty signal before increasing weight

## Files to Modify

### Core Implementation
1. `backend/app/agents/extractor.py` - Enhanced scoring logic, LLM uncertainty prompts
2. `backend/app/core/config.py` - HITL thresholds, field weights, timeout settings
3. `backend/app/orchestration/orchestration_agent.py` - Three-tier decision logic

### HITL Infrastructure  
4. `backend/app/models/hitl.py` - HITL session models and enums
5. `backend/app/api/v1/endpoints/hitl.py` - HITL session management endpoints
6. `backend/app/services/hitl_service.py` - Async pause/resume logic
7. `backend/app/storage/redis_client.py` - Redis session storage
8. `backend/app/storage/hitl_repository.py` - Database audit trail

### Frontend Implementation
**⚠️ Scope Decision Required:**

**Option A: Full Frontend Scope (Additional 2-3 weeks)**
9. `frontend/components/hitl/ReviewInterface.tsx` - Field-level confidence indicators, smart defaults, three action modes
10. `frontend/hooks/useHITLNotifications.ts` - WebSocket notifications
11. `frontend/components/hitl/ConfidenceBadge.tsx` - Color-coded confidence levels
12. `frontend/components/hitl/QuickActions.tsx` - "Accept All", "Fix Only Low Confidence", "Full Review"
13. `frontend/pages/hitl/Queue.tsx` - HITL queue management interface

**Option B: API-Only Scope (Backend Only)**
- Document API endpoints for future frontend implementation
- Provide Postman collection and API documentation
- Frontend team implements in separate sprint

**Recommendation:** Start with Option B for v1, schedule Option A for v1.1

### Database Schema
10. `backend/app/schemas/hitl.py` - HITL database schemas
11. Database migrations for HITL sessions table

### Observability (Phase 1)
12. `backend/app/core/logging.py` - HITL-specific logging configuration

## Key Design Decisions Addressed

✅ **Scoring Formula:** Field-weighted completeness + LLM uncertainty with 0.0 floor  
✅ **Async Pattern:** Complete pause/resume with session state management  
✅ **Warning Band:** Made actionable with "needs_review" flag and UI indicators  
✅ **Feedback Loop:** Comprehensive analytics logging for threshold calibration  
✅ **Validation Separation:** Explicit error handling before confidence scoring  

This plan provides a complete HITL system that addresses the original gaps while maintaining pipeline reliability and enabling continuous improvement through data-driven threshold tuning.
