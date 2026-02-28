"""Configuration for mock mode in agents."""

import os
from typing import Optional


class MockConfig:
    """Configuration for mock mode."""
    
    @staticmethod
    def is_mock_enabled() -> bool:
        """Check if mock mode is enabled.
        
        Returns:
            True if mock mode is enabled
        """
        return os.getenv("MOCK_GEMINI", "false").lower() in ("true", "1", "yes")
    
    @staticmethod
    def get_mock_responses_file() -> Optional[str]:
        """Get path to custom mock responses file.
        
        Returns:
            Path to mock responses file or None
        """
        return os.getenv("MOCK_RESPONSES_FILE")
    
    @staticmethod
    def should_log_mock_calls() -> bool:
        """Check if mock calls should be logged.
        
        Returns:
            True if mock calls should be logged
        """
        return os.getenv("LOG_MOCK_CALLS", "true").lower() in ("true", "1", "yes")
