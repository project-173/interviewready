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
    DATABASE_URL: str = "postgresql://user:password@localhost/interviewready"
    
    # Google Cloud / Vertex AI Configuration
    GOOGLE_PROJECT_ID: str = "architecting-ai-systems-e71af"
    GOOGLE_LOCATION: str = "us-central1"
    GOOGLE_CREDENTIALS_URI: Optional[str] = None
    
    # Gemini Model Configuration
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GOOGLE_API_KEY: str
    GEMINI_API_KEY: str
    
    # Firebase Configuration
    FIREBASE_ENABLED: bool = False
    FIREBASE_CONFIG_PATH: str = "classpath:architecting-ai-systems-e71af-firebase-adminsdk-fbsvc-0033ba2601.json"
    FIREBASE_PROJECT_ID: str
    FIREBASE_PRIVATE_KEY_ID: str
    FIREBASE_PRIVATE_KEY: str
    FIREBASE_CLIENT_EMAIL: str
    FIREBASE_CLIENT_ID: str
    FIREBASE_AUTH_URI: str = "https://accounts.google.com/o/oauth2/auth"
    FIREBASE_TOKEN_URI: str = "https://oauth2.googleapis.com/token"
    
    # Security
    SECURITY_FILTER_ORDER: int = 5
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Logging & Monitoring
    LOG_LEVEL: str = "DEBUG"
    LOGGERS: List[str] = ["app"]  # Equivalent to com.agent.backend
    ENABLE_HEALTH_ENDPOINT: bool = True
    ENABLE_INFO_ENDPOINT: bool = True
    ENABLE_METRICS_ENDPOINT: bool = True
    
    # LangGraph
    LANGGRAPH_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()
