"""Resume-related models."""

from typing import Optional, List
from pydantic import BaseModel, Field
from .base import Contact, Experience, Education, Project, Certification, Award


class Resume(BaseModel):
    """Resume model containing core resume sections."""

    skills: List[str] = Field(default_factory=list)
    experiences: List[Experience] = Field(default_factory=list)
    educations: List[Education] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    certifications: List[Certification] = Field(default_factory=list)
    awards: List[Award] = Field(default_factory=list)
