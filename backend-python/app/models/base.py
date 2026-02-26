"""Base models for resume components."""

from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field


class Contact(BaseModel):
    """Contact information model."""
    
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None


class Experience(BaseModel):
    """Work experience model."""
    
    title: Optional[str] = None
    company: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None


class Education(BaseModel):
    """Education model."""
    
    school: Optional[str] = None
    degree: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    gpa: Optional[float] = None
    gpa_max: Optional[float] = None
    description: Optional[str] = None


class Project(BaseModel):
    """Project model."""
    
    title: Optional[str] = None
    description: Optional[str] = None
    technologies: Optional[List[str]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    url: Optional[str] = None


class Certification(BaseModel):
    """Certification model."""
    
    name: Optional[str] = None
    issuer: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    credential_id: Optional[str] = None
    url: Optional[str] = None


class Award(BaseModel):
    """Award model."""
    
    title: Optional[str] = None
    issuer: Optional[str] = None
    date: Optional[date] = None
    description: Optional[str] = None


class Source(BaseModel):
    """Source reference model."""
    
    title: Optional[str] = None
    url: Optional[str] = None
    snippet: Optional[str] = None
    relevance_score: Optional[float] = None
