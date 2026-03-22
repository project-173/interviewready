"""Agent-related models."""

from enum import Enum
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator
from dataclasses import field
from .resume import Resume


class AgentResponse(BaseModel):
    """Agent response model with SHARP compliance data."""

    agent_name: Optional[str] = None
    content: Optional[str] = None
    reasoning: Optional[str] = None  # Explainability
    confidence_score: Optional[float] = None  # Confidence Indicator
    decision_trace: Optional[List[str]] = Field(default_factory=list)  # Auditability
    sharp_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict
    )  # SHARP Compliance Data


class ChatApiResponse(BaseModel):
    """External API response model for frontend consumption."""

    agent: Optional[str] = None
    payload: Optional[Dict[str, Any] | List[Any] | str] = None


class InterviewMessage(BaseModel):
    """Interview coaching message."""

    role: Optional[str] = Field(default=None, max_length=50)
    text: Optional[str] = Field(default=None, max_length=4000)


class ResumeFile(BaseModel):
    """Uploaded resume file payload."""

    data: str = Field(..., max_length=15000000)
    fileType: Literal["pdf"] = "pdf"


class ChatRequest(BaseModel):
    """Chat request model with rich JSON structure."""

    intent: Literal[
        "RESUME_CRITIC",
        "CONTENT_STRENGTH",
        "ALIGNMENT",
        "INTERVIEW_COACH",
    ]
    resumeData: Optional[Resume] = None
    resumeFile: Optional[ResumeFile] = None
    jobDescription: Optional[str] = Field(default="", max_length=20000)
    messageHistory: Optional[List[InterviewMessage]] = Field(default_factory=list)
    audioData: Optional[bytes] = None

    @field_validator('audioData', mode='before')
    @classmethod
    def decode_audio_data(cls, v):
        if isinstance(v, str):
            import base64
            return base64.b64decode(v)
        return v  # Audio data for interview coaching


class ResumeDocument(BaseModel):
    """Normalized resume document (lite)."""

    id: Optional[str] = None
    source: Optional[str] = None
    raw_text: Optional[str] = None
    parse_confidence: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)
    sections: Optional[Dict[str, str]] = None
    spans: Optional[List[Dict[str, Any]]] = None


class AnalysisArtifact(BaseModel):
    """Structured output captured from an agent."""

    agent: Optional[str] = None
    artifact_type: Optional[str] = None
    payload: Optional[Dict[str, Any] | List[Any] | str] = None
    confidence_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActionPlan(BaseModel):
    """Synthesis plan for resume edits or next steps."""

    summary: Optional[str] = None
    actions: List[str] = Field(default_factory=list)
    priority: Optional[str] = None
    no_change: Optional[bool] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizationFailure(BaseModel):
    """Normalization failure details."""

    reason: str
    recovery_steps: Optional[str] = None
    details: Optional[str] = None


class ResumeDocument(BaseModel):
    """Normalized resume document (lite)."""

    id: Optional[str] = None
    source: Optional[str] = None
    raw_text: Optional[str] = None
    parse_confidence: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)
    sections: Optional[Dict[str, str]] = None
    spans: Optional[List[Dict[str, Any]]] = None


class AnalysisArtifact(BaseModel):
    """Structured output captured from an agent."""

    agent: Optional[str] = None
    artifact_type: Optional[str] = None
    payload: Optional[Dict[str, Any] | List[Any] | str] = None
    confidence_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActionPlan(BaseModel):
    """Synthesis plan for resume edits or next steps."""

    summary: Optional[str] = None
    actions: List[str] = Field(default_factory=list)
    priority: Optional[str] = None
    no_change: Optional[bool] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizationFailure(BaseModel):
    """Normalization failure details."""

    reason: str
    recovery_steps: Optional[str] = None
    details: Optional[str] = None


class AlignmentReport(BaseModel):
    """Job alignment analysis report."""

    skillsMatch: Optional[List[str]] = Field(default_factory=list)
    missingSkills: Optional[List[str]] = Field(default_factory=list)
    experienceMatch: Optional[str] = None
    fitScore: Optional[int] = None
    reasoning: Optional[str] = None


class ContentSuggestion(BaseModel):
    """Faithful phrasing suggestion for resume improvement."""

    location: str
    original: str
    suggested: str
    evidenceStrength: Literal["HIGH", "MEDIUM", "LOW"]
    type: Literal["action_verb", "specificity", "structure", "redundancy"]


class ContentStrengthReport(BaseModel):
    """Content strength analysis report."""

    suggestions: List[ContentSuggestion]
    summary: str
    score: Optional[int] = None


class ResumeCriticIssue(BaseModel):
    """Resume critic issue."""
    
    location: str
    type: Literal["ats", "structure", "impact", "readability"]
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    description: str

class ResumeCriticReport(BaseModel):
    """Resume critic analysis report."""

    issues: List[ResumeCriticIssue]
    summary: str
    score: Optional[int] = None

class WorkflowStatus(BaseModel):
    """Workflow execution status."""

    session_id: Optional[str] = None
    current_agent: Optional[str] = None
    status: Optional[str] = None  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    progress_percentage: Optional[float] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

class AgentInput(BaseModel):
    """Structured input passed from the orchestrator to individual agents."""

    intent: Literal[
        "RESUME_CRITIC",
        "CONTENT_STRENGTH",
        "ALIGNMENT",
        "INTERVIEW_COACH",
    ]
    resume: Optional[Resume] = None
    resume_document: Optional[ResumeDocument] = None
    job_description: str = ""
    message_history: List[InterviewMessage] = field(default_factory=list)
    audio_data: Optional[bytes] = None

class Intent(str, Enum):
    RESUME_CRITIC = "RESUME_CRITIC"
    CONTENT_STRENGTH = "CONTENT_STRENGTH"
    ALIGNMENT = "ALIGNMENT"
    INTERVIEW_COACH = "INTERVIEW_COACH"