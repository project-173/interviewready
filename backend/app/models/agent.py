"""Agent-related models."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from .base import Source


class AgentResponse(BaseModel):
    """Agent response model with SHARP compliance data."""
    
    agent_name: Optional[str] = None
    content: Optional[str] = None
    reasoning: Optional[str] = None  # Explainability
    confidence_score: Optional[float] = None  # Confidence Indicator
    decision_trace: Optional[List[str]] = Field(default_factory=list)  # Auditability
    sharp_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)  # SHARP Compliance Data


class InterviewMessage(BaseModel):
    """Interview coaching message."""
    
    role: Optional[str] = None
    text: Optional[str] = None


class ChatRequest(BaseModel):
    """Chat request model with rich JSON structure."""
    
    intent: str  # 'RESUME_CRITIC' | 'CONTENT_STRENGTH' | 'ALIGNMENT' | 'INTERVIEW_COACH'
    resumeData: Optional[Dict[str, Any]] = Field(default_factory=dict)
    jobDescription: Optional[str] = ""
    messageHistory: Optional[List[InterviewMessage]] = Field(default_factory=list)


class AlignmentReport(BaseModel):
    """Job alignment analysis report."""
    
    overall_score: Optional[float] = None
    matching_keywords: Optional[List[str]] = Field(default_factory=list)
    missing_keywords: Optional[List[str]] = Field(default_factory=list)
    role_fit_analysis: Optional[str] = None
    sources: Optional[List[Source]] = Field(default_factory=list)


class ContentAnalysisReport(BaseModel):
    """Content strength analysis report."""
    
    strengths: Optional[List[str]] = Field(default_factory=list)
    gaps: Optional[List[str]] = Field(default_factory=list)
    skill_improvements: Optional[List[str]] = Field(default_factory=list)
    quantified_impact_score: Optional[float] = None


class StructuralAssessment(BaseModel):
    """Resume structural assessment."""
    
    overall_score: Optional[float] = None
    format_issues: Optional[List[str]] = Field(default_factory=list)
    completeness_score: Optional[float] = None
    readability_score: Optional[float] = None
    recommendations: Optional[List[str]] = Field(default_factory=list)


class WorkflowStatus(BaseModel):
    """Workflow execution status."""
    
    session_id: Optional[str] = None
    current_agent: Optional[str] = None
    status: Optional[str] = None  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    progress_percentage: Optional[float] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
