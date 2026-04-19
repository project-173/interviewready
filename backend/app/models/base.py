"""Base models for resume components."""

from pydantic import BaseModel, Field


class Work(BaseModel):
    """Work history entry (JSON Resume: work)."""

    name: str | None = None
    position: str | None = None
    url: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    highlights: list[str] = Field(default_factory=list)


class Education(BaseModel):
    """Education entry (JSON Resume: education)."""

    institution: str | None = None
    url: str | None = None
    area: str | None = None
    studyType: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    score: str | None = None
    courses: list[str] = Field(default_factory=list)


class Award(BaseModel):
    """Award entry (JSON Resume: awards)."""

    title: str | None = None
    date: str | None = None
    awarder: str | None = None
    summary: str | None = None


class Certificate(BaseModel):
    """Certificate entry (JSON Resume: certificates)."""

    name: str | None = None
    date: str | None = None
    issuer: str | None = None
    url: str | None = None


class Skill(BaseModel):
    """Skill entry (JSON Resume: skills)."""

    name: str | None = None


class Project(BaseModel):
    """Project entry (JSON Resume: projects)."""

    name: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    description: str | None = None
    highlights: list[str] = Field(default_factory=list)
    url: str | None = None


class Source(BaseModel):
    """Source reference model."""

    title: str | None = None
    url: str | None = None
    snippet: str | None = None
    relevance_score: float | None = None
