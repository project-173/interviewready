"""Resume-related models."""

from typing import List
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
    """JSON Resume-compatible model (basics excluded)."""

    work: List[Work] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    awards: List[Award] = Field(default_factory=list)
    certificates: List[Certificate] = Field(default_factory=list)
    skills: List[Skill] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
