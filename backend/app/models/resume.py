"""Resume-related models."""

from typing import Optional, List
from pydantic import BaseModel, Field
from .base import Contact, Experience, Education, Project, Certification, Award


class Resume(BaseModel):
    """Resume model containing all resume information."""

    id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    title: Optional[str] = None
    isMaster: Optional[bool] = False
    summary: Optional[str] = None
    timestamp: Optional[str] = None

    skills: List[str] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    certifications: List[Certification] = Field(default_factory=list)
    awards: List[Award] = Field(default_factory=list)

    # Backward compatibility properties kept for existing consumers.
    contact: Optional[Contact] = None
    experiences: Optional[List[Experience]] = Field(default_factory=list)
    educations: Optional[List[Education]] = Field(default_factory=list)
