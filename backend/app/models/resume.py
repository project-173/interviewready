"""Resume-related models."""

from typing import Optional, List
from pydantic import BaseModel, Field
from .base import Contact, Experience, Education, Project, Certification, Award


class Resume(BaseModel):
    """Resume model containing all resume information."""
    
    id: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    is_master: Optional[bool] = False
    
    skills: Optional[List[str]] = Field(default_factory=list)
    experiences: Optional[List[Experience]] = Field(default_factory=list)
    educations: Optional[List[Education]] = Field(default_factory=list)
    projects: Optional[List[Project]] = Field(default_factory=list)
    certifications: Optional[List[Certification]] = Field(default_factory=list)
    awards: Optional[List[Award]] = Field(default_factory=list)
    
    contact: Optional[Contact] = None
