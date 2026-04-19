"""Pydantic models for InterviewReady Backend."""

from .agent import (
    ActionPlan,
    AgentInput,
    AgentResponse,
    AlignmentReport,
    AnalysisArtifact,
    ChatApiResponse,
    ChatRequest,
    ContentStrengthReport,
    InterviewMessage,
    NormalizationFailure,
    ResumeCriticReport,
    ResumeDocument,
    ResumeFile,
    WorkflowStatus,
)
from .base import Award, Certificate, Education, Project, Skill, Source, Work
from .database import (
    AwardModel,
    Base,
    CertificationModel,
    EducationModel,
    ExperienceModel,
    ProjectModel,
    ResumeModel,
)
from .resume import Resume
from .session import SessionContext, SharedState

__all__ = [
    "ActionPlan",
    "AgentInput",
    # Agent models
    "AgentResponse",
    "AlignmentReport",
    "AnalysisArtifact",
    "Award",
    "AwardModel",
    "Base",
    "Certificate",
    "CertificationModel",
    "ChatApiResponse",
    "ChatRequest",
    "ContentStrengthReport",
    "Education",
    "EducationModel",
    "ExperienceModel",
    "InterviewMessage",
    "NormalizationFailure",
    "Project",
    "ProjectModel",
    # Resume models
    "Resume",
    "ResumeCriticReport",
    "ResumeDocument",
    "ResumeFile",
    # SQLAlchemy models (optional)
    "ResumeModel",
    # Session models
    "SessionContext",
    "SharedState",
    "Skill",
    "Source",
    # Base models
    "Work",
    "WorkflowStatus",
]
