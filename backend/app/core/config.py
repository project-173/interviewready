"""Application configuration settings."""

from pydantic import ConfigDict
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
    
    # Google Cloud / Vertex AI Configuration
    GOOGLE_PROJECT_ID: str = "your-project-id"
    GOOGLE_LOCATION: str = "asia-southeast1"
    GOOGLE_CREDENTIALS_URI: Optional[str] = None
    
    # Gemini Model Configuration
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_API_KEY: str
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
    
    # Security
    AUTH_DISABLED_USER_ID: str = "dev-user"
    
    # Logging & Monitoring
    LOG_LEVEL: str = "DEBUG"
    LOGGERS: List[str] = ["app"]  # Equivalent to com.agent.backend
    ENABLE_HEALTH_ENDPOINT: bool = True
    ENABLE_INFO_ENDPOINT: bool = True
    ENABLE_METRICS_ENDPOINT: bool = True
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True
    )


# Create settings instance
settings = Settings()
