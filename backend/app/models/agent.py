"""Agent-related models."""

from dataclasses import field
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .resume import Resume


class AgentResponse(BaseModel):
    """Agent response model with SHARP compliance data."""

    agent_name: str | None = None
    content: str | None = None
    reasoning: str | None = None  # Explainability
    confidence_score: float | None = None  # Confidence Indicator
    needs_review: bool | None = None
    low_confidence_fields: list[str] | None = Field(default_factory=list)
    decision_trace: list[str] | None = Field(default_factory=list)  # Auditability
    sharp_metadata: dict[str, Any] | None = Field(
        default_factory=dict
    )  # SHARP Compliance Data


class ChatApiResponse(BaseModel):
    """External API response model for frontend consumption."""

    agent: str | None = None
    payload: dict[str, Any] | list[Any] | str | None = None
    confidence_score: float | None = None
    needs_review: bool | None = None
    low_confidence_fields: list[str] | None = Field(default_factory=list)
    metadata: dict[str, Any] | None = Field(default_factory=dict)


class InterviewMessage(BaseModel):
    """Interview coaching message."""

    role: str | None = Field(default=None, max_length=50)
    text: str | None = Field(default=None, max_length=4000)


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
    control: Literal["resume", "rewind"] | None = None
    checkpointId: str | None = None
    resumeData: Resume | None = None
    resumeFile: ResumeFile | None = None
    jobDescription: str | None = Field(default="", max_length=20000)
    messageHistory: list[InterviewMessage] | None = Field(default_factory=list)
    audioData: bytes | None = None

    @field_validator("audioData", mode="before")
    @classmethod
    def decode_audio_data(cls, v):
        if isinstance(v, str):
            import base64

            decoded = base64.b64decode(v)
        else:
            decoded = v

        if decoded is None:
            return None

        # Convert PCM to WAV if not already WAV
        from app.utils.audio_utils import pcm_to_wav, validate_audio_format

        if not validate_audio_format(decoded):
            # Assume it's PCM and convert to WAV
            decoded = pcm_to_wav(decoded)

        return decoded


class ResumeDocument(BaseModel):
    """Normalized resume document (lite)."""

    id: str | None = None
    source: str | None = None
    raw_text: str | None = None
    parse_confidence: float | None = None
    warnings: list[str] = Field(default_factory=list)
    sections: dict[str, str] | None = None
    spans: list[dict[str, Any]] | None = None


class AnalysisArtifact(BaseModel):
    """Structured output captured from an agent."""

    agent: str | None = None
    artifact_type: str | None = None
    payload: dict[str, Any] | list[Any] | str | None = None
    confidence_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActionPlan(BaseModel):
    """Synthesis plan for resume edits or next steps."""

    summary: str | None = None
    actions: list[str] = Field(default_factory=list)
    priority: str | None = None
    no_change: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizationFailure(BaseModel):
    """Normalization failure details."""

    reason: str
    recovery_steps: str | None = None
    details: str | None = None


class AlignmentReport(BaseModel):
    """Job alignment analysis report."""

    skillsMatch: list[str] | None = Field(default_factory=list)
    missingSkills: list[str] | None = Field(default_factory=list)
    experienceMatch: list[str] | None = Field(default_factory=list)
    summary: str | None = None


class ContentSkill(BaseModel):
    """Skill evidence extracted from the resume."""

    name: str
    category: str
    confidenceScore: float
    evidenceStrength: Literal["HIGH", "MEDIUM", "LOW"]
    evidence: str


class ContentAchievement(BaseModel):
    """Achievement evidence extracted from the resume."""

    description: str
    impact: Literal["HIGH", "MEDIUM", "LOW"]
    quantifiable: bool
    confidenceScore: float
    originalText: str


class ContentSuggestion(BaseModel):
    """Faithful phrasing suggestion for resume improvement."""

    location: str
    original: str
    suggested: str
    evidenceStrength: Literal["HIGH", "MEDIUM", "LOW"]
    type: Literal["action_verb", "specificity", "structure", "redundancy"]


class ContentStrengthReport(BaseModel):
    """Content strength analysis report."""

    suggestions: list[ContentSuggestion] = Field(default_factory=list)
    summary: str = ""
    score: int | None = None


class ResumeCriticIssue(BaseModel):
    """Resume critic issue."""

    location: str
    type: Literal["ats", "structure", "impact", "readability"]
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    description: str


class ResumeCriticReport(BaseModel):
    """Resume critic analysis report."""

    issues: list[ResumeCriticIssue] = Field(default_factory=list)
    summary: str = ""
    score: int | None = None


class WorkflowStatus(BaseModel):
    """Workflow execution status."""

    session_id: str | None = None
    current_agent: str | None = None
    status: str | None = None  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    progress_percentage: float | None = None
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class AgentInput(BaseModel):
    """Structured input passed from the orchestrator to individual agents."""

    intent: Literal[
        "RESUME_CRITIC",
        "CONTENT_STRENGTH",
        "ALIGNMENT",
        "INTERVIEW_COACH",
    ]
    resume: Resume | None = None
    resume_document: ResumeDocument | None = None
    job_description: str = ""
    message_history: list[InterviewMessage] = field(default_factory=list)
    audio_data: bytes | None = None


class Intent(StrEnum):
    RESUME_CRITIC = "RESUME_CRITIC"
    CONTENT_STRENGTH = "CONTENT_STRENGTH"
    ALIGNMENT = "ALIGNMENT"
    INTERVIEW_COACH = "INTERVIEW_COACH"
