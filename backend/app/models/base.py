"""Base models for resume components."""

from typing import Optional, List
from pydantic import BaseModel, Field


class Work(BaseModel):
    """Work history entry (JSON Resume: work)."""

    name: Optional[str] = None
    position: Optional[str] = None
    url: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    summary: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)


class Volunteer(BaseModel):
    """Volunteer entry (JSON Resume: volunteer)."""

    organization: Optional[str] = None
    position: Optional[str] = None
    url: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    summary: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)


class Education(BaseModel):
    """Education entry (JSON Resume: education)."""

    institution: Optional[str] = None
    url: Optional[str] = None
    area: Optional[str] = None
    studyType: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    score: Optional[str] = None
    courses: List[str] = Field(default_factory=list)


class Award(BaseModel):
    """Award entry (JSON Resume: awards)."""

    title: Optional[str] = None
    date: Optional[str] = None
    awarder: Optional[str] = None
    summary: Optional[str] = None


class Certificate(BaseModel):
    """Certificate entry (JSON Resume: certificates)."""

    name: Optional[str] = None
    date: Optional[str] = None
    issuer: Optional[str] = None
    url: Optional[str] = None


class Publication(BaseModel):
    """Publication entry (JSON Resume: publications)."""

    name: Optional[str] = None
    publisher: Optional[str] = None
    releaseDate: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None


class Skill(BaseModel):
    """Skill entry (JSON Resume: skills)."""

    name: Optional[str] = None
    level: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)


class Language(BaseModel):
    """Language entry (JSON Resume: languages)."""

    language: Optional[str] = None
    fluency: Optional[str] = None


class Interest(BaseModel):
    """Interest entry (JSON Resume: interests)."""

    name: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)


class Reference(BaseModel):
    """Reference entry (JSON Resume: references)."""

    name: Optional[str] = None
    reference: Optional[str] = None


class Project(BaseModel):
    """Project entry (JSON Resume: projects)."""

    name: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    description: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)
    url: Optional[str] = None


class Source(BaseModel):
    """Source reference model."""

    title: Optional[str] = None
    url: Optional[str] = None
    snippet: Optional[str] = None
    relevance_score: Optional[float] = None
