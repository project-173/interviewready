"""SQLAlchemy ORM models (optional, for future database use)."""

from datetime import date
from typing import List
from sqlalchemy import Column, String, Float, Boolean, Date, Text, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class ResumeModel(Base):
    """SQLAlchemy Resume model."""
    
    __tablename__ = "resumes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String)
    summary = Column(Text)
    is_master = Column(Boolean, default=False)
    skills = Column(JSON)  # List[str]
    
    # Relationships
    experiences = relationship("ExperienceModel", back_populates="resume", cascade="all, delete-orphan")
    educations = relationship("EducationModel", back_populates="resume", cascade="all, delete-orphan")
    projects = relationship("ProjectModel", back_populates="resume", cascade="all, delete-orphan")
    certifications = relationship("CertificationModel", back_populates="resume", cascade="all, delete-orphan")
    awards = relationship("AwardModel", back_populates="resume", cascade="all, delete-orphan")


class ExperienceModel(Base):
    """SQLAlchemy Experience model."""
    
    __tablename__ = "resume_experiences"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    resume_id = Column(String, ForeignKey("resumes.id"))
    title = Column(String)
    company = Column(String)
    start_date = Column(Date)
    end_date = Column(Date, nullable=True)
    description = Column(Text)
    
    # Relationship
    resume = relationship("ResumeModel", back_populates="experiences")


class EducationModel(Base):
    """SQLAlchemy Education model."""
    
    __tablename__ = "resume_educations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    resume_id = Column(String, ForeignKey("resumes.id"))
    school = Column(String)
    degree = Column(String)
    start_date = Column(Date)
    end_date = Column(Date, nullable=True)
    gpa = Column(Float)
    gpa_max = Column(Float)
    description = Column(Text)
    
    # Relationship
    resume = relationship("ResumeModel", back_populates="educations")


class ProjectModel(Base):
    """SQLAlchemy Project model."""
    
    __tablename__ = "resume_projects"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    resume_id = Column(String, ForeignKey("resumes.id"))
    title = Column(String)
    description = Column(Text)
    technologies = Column(JSON)  # List[str]
    start_date = Column(Date)
    end_date = Column(Date, nullable=True)
    url = Column(String)
    
    # Relationship
    resume = relationship("ResumeModel", back_populates="projects")


class CertificationModel(Base):
    """SQLAlchemy Certification model."""
    
    __tablename__ = "resume_certifications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    resume_id = Column(String, ForeignKey("resumes.id"))
    name = Column(String)
    issuer = Column(String)
    issue_date = Column(Date)
    expiry_date = Column(Date, nullable=True)
    credential_id = Column(String)
    url = Column(String)
    
    # Relationship
    resume = relationship("ResumeModel", back_populates="certifications")


class AwardModel(Base):
    """SQLAlchemy Award model."""
    
    __tablename__ = "resume_awards"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    resume_id = Column(String, ForeignKey("resumes.id"))
    title = Column(String)
    issuer = Column(String)
    date = Column(Date)
    description = Column(Text)
    
    # Relationship
    resume = relationship("ResumeModel", back_populates="awards")
