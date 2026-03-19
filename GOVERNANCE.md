# Agent Governance & Traceability

## Explainability & Traceability

### How does the solution ensure explainability and traceability of agent decisions?

**Implementation:**
- **Langfuse Integration**: Every agent decision is captured in Langfuse traces with complete context
  - `session_id`: Links all decisions within a user session
  - `metadata`: Includes agent name, decision rationale, input/output
  - `environment`: Distinguishes local/staging/production for audit trails
- **Agent Decision Logging**: Each agent records:
  - Input received
  - Processing steps
  - Scoring/ranking criteria used
  - Final decision with confidence level
  - Timestamp and version info
- **SHAP Governance Service**: Provides audit trails with:
  - Hallucination detection flags
  - Confidence threshold validation
  - Content strength validation
- **Trace Propagation**: `session_id` automatically propagated across all nested spans so every decision can be traced back to a user session

### Architecture:
```
User Request (session_id=abc)
    ↓ [Langfuse trace]
API Endpoint (/api/v1/chat)
    ↓ [trace.span with session_id propagated]
OrchestrationAgent
    ↓ [trace.span per agent]
ResumeCriticAgent → [decision logs, confidence, audit flags]
JobAlignmentAgent → [decision logs, confidence, audit flags]
InterviewCoachAgent → [decision logs, confidence, audit flags]
ContentStrengthAgent → [decision logs, confidence, audit flags]
    ↓ [all aggregated to single trace]
Response back to user [with decision trail in Langfuse]
```

---

## Safeguards: Bias, Fairness, Accountability, Trust, Assurance

### What safeguards are in place?

**1. Governance Audit Service** (`app/governance/sharp_governance_service.py`)
- **Hallucination Detection**: Flags responses that make unsupported claims
- **Confidence Thresholds**: Only accepts decisions above minimum confidence (default: 0.3)
- **Quantifiable Pattern Validation**: Ensures claims with numbers are supported
- **Content Strength Validation**: Agent-specific quality checks

**2. Bias Mitigation**
- **NLI (Natural Language Inference)** in `app/utils/`: Validates logic consistency
- **SHAP Analysis**: Feature importance analysis to detect skewed decision factors
- **Prompt Versioning**: All prompts tracked in Langfuse (`create_prompt()`) so drift is detectable
- **Multi-Agent Consensus**: Different agents evaluate same input; disagreements flagged

**3. Accountability**
- **Session Tracking**: Every decision linked to `session_id` for traceability
- **Audit Timestamps**: Every decision timestamped for accountability
- **Error Logging**: Failures recorded with full context
- **Environment Tagging**: `production` vs `staging` clearly marked

**4. Trust**
- **Confidence Scoring**: Responses include confidence levels
- **Reasoning Capture**: Agent reasoning steps recorded in spans
- **Metadata Transparency**: All input/output stored in Langfuse for verification
- **Versioning**: `APP_VERSION` and `environment` tracked per trace

**5. Assurance**
- **Pre-Deployment Tests**: Golden set E2E tests with known good/bad cases
- **Production Monitoring**: Real-time Langfuse dashboards for anomaly detection
- **Automated Guardrails**: SHARP governance service blocks low-confidence responses

---

## Common Services (Shared Memory, Logs)

### What reusable infrastructure is required?

**1. Langfuse (Observability & Tracing)**
- Central service for all trace data
- Enables cross-agent decision correlation
- Provides session-level aggregation
- Supports prompt versioning and experiment tracking

**2. Session Storage** (`app/api/v1/session_store.py`)
- Shared session context across agents
- Maintains user-specific state (resume, JD, preferences)
- Propagates `session_id` to all agents

**3. Logging Service** (`app/core/logging.py`)
- Centralized structured logging
- Compatible with Langfuse metadata
- Enables log-level filtering by environment

**4. Firebase/Auth** (`app/core/auth.py`)
- User identity tracking
- Session ownership validation
- Access control for accountability

**5. Configuration Management** (`app/core/config.py`)
- Centralized settings (Langfuse keys, model versions, thresholds)
- Environment-aware configuration (local/staging/production)
- Feature flags for A/B testing governance rules

---

## Reusable Libraries & Frameworks

### What frameworks power the agent orchestration?

**1. LangGraph** (`app/orchestration/orchestration_agent.py`)
- **Purpose**: Stateful agent orchestration and workflow management
- **Usage**: Coordinates multi-agent workflow with state persistence
- **Tracing**: Integrated with `langfuse.trace()` at orchestration level
- **Benefit**: Checkpoint-based recovery and deterministic re-runs

**2. LangChain** (if used)
- **Purpose**: LLM chains and tools
- **Integration**: Agents built on LangChain utilities
- **Tracing**: Compatible with Langfuse via SDK integration

**3. Pydantic v2** (`app/models/`)
- **Purpose**: Schema validation and serialization
- **Usage**: Type-safe agent requests/responses
- **Tracing**: Automatic metadata extraction from models

**4. FastAPI** (`app/api/`)
- **Purpose**: HTTP API layer
- **Tracing**: Wrapped endpoints with `langfuse.propagate_attributes(session_id=...)`
- **Benefit**: Clean async/await support for agent calls

**5. Custom Utilities**
- **NLI Service** (`app/utils/`): Natural Language Inference for consistency checking
- **PDF Parser** (`app/utils/pdf_parser.py`): Resume extraction
- **JSON Parser** (`app/utils/json_parser.py`): Response parsing

---

## Integration with Langfuse

Each layer adds governance metadata to traces:

```python
# API Layer - establishes session context
with langfuse.propagate_attributes(session_id="user-abc"):
    with langfuse.trace(name="chat_api_request", metadata={
        "user_id": get_current_user,
        "endpoint": "/api/v1/chat",
    }) as trace:
        
        # Orchestration Layer - coordinates agents
        with langfuse.trace(name="orchestration", metadata={
            "strategy": "multi-agent-consensus",
        }) as orch_trace:
            
            # Agent Layer - records individual decisions
            with langfuse.trace(name="ResumeCriticAgent_process", metadata={
                "agent": "ResumeCriticAgent",
                "input_length": len(input),
            }) as agent_trace:
                response = agent.process(input, context)
                agent_trace.update(output={
                    "confidence": response.confidence,
                    "audit": governance_check,
                })
```

**Result**: Complete decision trail in Langfuse, filterable by:
- `session_id` (trace back user session)
- `environment` (production vs staging)
- `agent` (which agent made the decision)
- `confidence` (decision quality)
- `audit` flags (bias/hallucination markers)

---

## Deployment Assurance

| Layer | Checklist |
|-------|-----------|
| **Local** | `APP_ENV=local` in `.env`, Langfuse optional |
| **Staging** | `APP_ENV=staging` on `langfuse` branch, Langfuse required |
| **Production** | Would be `APP_ENV=production` (separate workflow) |

**Monitoring**: Use Langfuse dashboards to:
- Filter traces by environment
- Monitor confidence trends
- Alert on audit failures
- Compare agent performance across versions
