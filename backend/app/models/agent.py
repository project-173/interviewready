"""Agent-related models."""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator
from .resume import Resume


class AgentResponse(BaseModel):
    """Agent response model with SHARP compliance data."""
    
    agent_name: Optional[str] = None
    content: Optional[str] = None
    reasoning: Optional[str] = None  # Explainability
    confidence_score: Optional[float] = None  # Confidence Indicator
    decision_trace: Optional[List[str]] = Field(default_factory=list)  # Auditability
    sharp_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)  # SHARP Compliance Data


class ChatApiResponse(BaseModel):
    """External API response model for frontend consumption."""

    agent: Optional[str] = None
    payload: Optional[Dict[str, Any] | List[Any] | str] = None


class InterviewMessage(BaseModel):
    """Interview coaching message."""
    
    role: Optional[str] = None
    text: Optional[str] = None


class ResumeFile(BaseModel):
    """Uploaded resume file payload."""

    data: str
    fileType: Literal["pdf"] = "pdf"


class ChatRequest(BaseModel):
    """Chat request model with rich JSON structure."""
    
    intent: str  # 'RESUME_CRITIC' | 'CONTENT_STRENGTH' | 'ALIGNMENT' | 'INTERVIEW_COACH'
    resumeData: Optional[Resume] = None
    resumeFile: Optional[ResumeFile] = None
    jobDescription: Optional[str] = ""
    messageHistory: Optional[List[InterviewMessage]] = Field(default_factory=list)
    audioData: Optional[bytes] = None
    
    @field_validator('audioData', mode='before')
    @classmethod
    def decode_audio_data(cls, v):
        if isinstance(v, str):
            import base64
            return base64.b64decode(v)
        return v  # Audio data for interview coaching


class AlignmentReport(BaseModel):
    """Job alignment analysis report."""

    skillsMatch: Optional[List[str]] = Field(default_factory=list)
    missingSkills: Optional[List[str]] = Field(default_factory=list)
    experienceMatch: Optional[str] = None
    fitScore: Optional[int] = None
    reasoning: Optional[str] = None


class ContentSkill(BaseModel):
    """Skill evidence extracted from the resume."""

    name: str
    category: Literal["Technical", "Soft", "Domain", "Tool"]
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

    original: str
    suggested: str
    rationale: str
    faithful: bool
    confidenceScore: float


class ContentAnalysisReport(BaseModel):
    """Content strength analysis report."""

    skills: Optional[List[ContentSkill]] = Field(default_factory=list)
    achievements: Optional[List[ContentAchievement]] = Field(default_factory=list)
    suggestions: Optional[List[ContentSuggestion]] = Field(default_factory=list)
    hallucinationRisk: Optional[float] = None
    summary: Optional[str] = None


class StructuralAssessment(BaseModel):
    """Resume structural assessment."""

    score: Optional[float] = None
    readability: Optional[str] = None
    formattingRecommendations: Optional[List[str]] = Field(default_factory=list)
    suggestions: Optional[List[str]] = Field(default_factory=list)


class WorkflowStatus(BaseModel):
    """Workflow execution status."""
    
    session_id: Optional[str] = None
    current_agent: Optional[str] = None
    status: Optional[str] = None  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    progress_percentage: Optional[float] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
