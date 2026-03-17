"""Application configuration settings."""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "agent-backend"
    DEBUG: bool = False
    VERSION: str = "1.0.0"
    SERVER_PORT: int = 8080
    
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
    
    # CORS
    ALLOWED_HOSTS: List[str] = [
        "http://localhost:3000", 
        "http://127.0.0.1:3000", 
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "https://interviewready-frontend-266623940622.asia-southeast1.run.app",
        "*" # In production Cloud Run, we can further restrict this to the actual frontend URL
    ]
    
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
