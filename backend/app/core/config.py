"""Application configuration settings."""

from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import List, Optional, Union
import os
import json


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "agent-backend"
    VERSION: str = "1.0.0"
    SERVER_PORT: int = 8080
    LOG_LEVEL: str = "DEBUG"
    APP_ENV: str = "local" # (e.g. local, staging, prod)

    # Google Configuration
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_AI_API_KEY: Optional[str] = None
    
    # CORS
    ALLOWED_HOSTS: Union[str, List[str]] = [
        "http://localhost:3000", 
        "http://127.0.0.1:3000", 
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "https://interviewready-frontend-266623940622.asia-southeast1.run.app",
        "https://interviewready-backend-266623940622.asia-southeast1.run.app",
        "https://interviewready-backend-bnlvcku7xq-as.a.run.app",
    ]

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def assemble_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.strip().startswith("["):
                try:
                    return json.loads(v.replace("'", '"'))
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Langfuse
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: Optional[str] = "https://cloud.langfuse.com"

    # Mock agent response
    MOCK_RESUME_CRITIC_AGENT: bool = False
    MOCK_EXTRACTOR_AGENT: bool = False
    MOCK_CONTENT_STRENGTH_AGENT: bool = False
    MOCK_JOB_ALIGNMENT_AGENT: bool = False
    MOCK_INTERVIEW_COACH_AGENT: bool = False

    # LLM Guard
    LLM_GUARD_ENABLED: bool = False

    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Sync Gemini API key if GOOGLE_AI_API_KEY is provided
if not settings.GEMINI_API_KEY and settings.GOOGLE_AI_API_KEY:
    settings.GEMINI_API_KEY = settings.GOOGLE_AI_API_KEY