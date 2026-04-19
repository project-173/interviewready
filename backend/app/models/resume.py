"""Resume-related models."""

from pydantic import BaseModel, Field

from .base import (
    Award,
    Certificate,
    Education,
    Project,
    Skill,
    Work,
)


class Resume(BaseModel):
    """JSON Resume-compatible model."""

    work: list[Work] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    awards: list[Award] = Field(default_factory=list)
    certificates: list[Certificate] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
