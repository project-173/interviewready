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
    DEBUG: bool = False
    VERSION: str = "1.0.0"
    SERVER_PORT: int = 8080

    # Deployment environment (helps to distinguish local dev vs cloud)
    # Set via env var `APP_ENV` (e.g. local, staging, prod)
    APP_ENV: str = "local"
    
    # Database
    DATABASE_URL: str = "sqlite:///./test.db"  # Use SQLite by default to ensure startup without Postgres
    
    # Google Cloud / Vertex AI Configuration
    GOOGLE_PROJECT_ID: str = "aaas-490414"
    GOOGLE_LOCATION: str = "asia-southeast1"
    GOOGLE_CREDENTIALS_URI: Optional[str] = None
    
    # Gemini Model Configuration
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_API_KEY: Optional[str] = None

    MOCK_GEMINI: bool = False
    LOG_MOCK_CALLS: bool = False
    
    # Firebase Configuration
    FIREBASE_ENABLED: bool = False
    FIREBASE_CONFIG_PATH: str = "classpath:architecting-ai-systems-e71af-firebase-adminsdk-fbsvc-0033ba2601.json"
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_PRIVATE_KEY_ID: Optional[str] = None
    FIREBASE_PRIVATE_KEY: Optional[str] = None
    FIREBASE_CLIENT_EMAIL: Optional[str] = None
    FIREBASE_CLIENT_ID: Optional[str] = None
    FIREBASE_AUTH_URI: str = "https://accounts.google.com/o/oauth2/auth"
    FIREBASE_TOKEN_URI: str = "https://oauth2.googleapis.com/token"
    
    # Security
    SECURITY_FILTER_ORDER: int = 5
    AUTH_ENABLED: bool = False
    AUTH_DISABLED_USER_ID: str = "dev-user"
    GOOGLE_AI_API_KEY: Optional[str] = None # Added for compatibility with user's secret name
    
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
    LANGFUSE_HOST: Optional[str] = "https://cloud.langfuse.com"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Sync Gemini API key if GOOGLE_AI_API_KEY is provided
if not settings.GEMINI_API_KEY and settings.GOOGLE_AI_API_KEY:
    settings.GEMINI_API_KEY = settings.GOOGLE_AI_API_KEY
