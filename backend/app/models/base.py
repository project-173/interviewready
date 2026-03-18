"""Base models for resume components."""

from typing import Optional, List
from pydantic import BaseModel, Field


class Contact(BaseModel):
    """Contact information model."""

    fullName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None


class Experience(BaseModel):
    """Work experience model."""

    company: Optional[str] = None
    role: Optional[str] = None
    duration: Optional[str] = None
    achievements: List[str] = Field(default_factory=list)


class Education(BaseModel):
    """Education model."""

    institution: Optional[str] = None
    degree: Optional[str] = None
    year: Optional[str] = None


class Project(BaseModel):
    """Project model."""

    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None


class Certification(BaseModel):
    """Certification model."""

    name: Optional[str] = None
    issuer: Optional[str] = None
    date: Optional[str] = None


class Award(BaseModel):
    """Award model."""

    title: Optional[str] = None
    issuer: Optional[str] = None
    date: Optional[str] = None


class Source(BaseModel):
    """Source reference model."""
    
    title: Optional[str] = None
    url: Optional[str] = None
    snippet: Optional[str] = None
    relevance_score: Optional[float] = None
