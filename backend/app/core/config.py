"""Application configuration settings."""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os
import json


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "agent-backend"
    DEBUG: bool = False
    VERSION: str = "1.0.0"
    SERVER_PORT: int = 8080
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/interviewready"
    
    # Google Cloud / Vertex AI Configuration
    GOOGLE_PROJECT_ID: str = "architecting-ai-systems-e71af"
    GOOGLE_LOCATION: str = "us-central1"
    GOOGLE_CREDENTIALS_URI: Optional[str] = None
    
    # Gemini Model Configuration
    GEMINI_MODEL: str = "gemini-2.5-flash"
    INTERVIEW_COACH_MODEL: str = "gemini-1.5-flash"  # Separate model for interview agent to manage rate limits
    GEMINI_API_KEY: str
    GOOGLE_AI_API_KEY: Optional[str] = None
    
    # Security
    SECURITY_FILTER_ORDER: int = 5
    AUTH_ENABLED: bool = True
    AUTH_DISABLED_USER_ID: str = "dev-user"
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
    
    # Logging & Monitoring
    LOG_LEVEL: str = "DEBUG"
    LOGGERS: List[str] = ["app"]  # Equivalent to com.agent.backend
    ENABLE_HEALTH_ENDPOINT: bool = True
    ENABLE_INFO_ENDPOINT: bool = True
    ENABLE_METRICS_ENDPOINT: bool = True
    
    # LangGraph
    LANGGRAPH_API_KEY: Optional[str] = None
    
    # Langfuse
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: Optional[str] = None
    
    # Environment
    APP_ENV: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Sync Gemini API key if GOOGLE_AI_API_KEY is provided
if not settings.GEMINI_API_KEY and settings.GOOGLE_AI_API_KEY:
    settings.GEMINI_API_KEY = settings.GOOGLE_AI_API_KEY
