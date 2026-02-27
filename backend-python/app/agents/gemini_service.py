"""Gemini API service for agent interactions."""

import os
import json
import re
from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types
from ..models.session import SessionContext


class GeminiService:
    """Service for interacting with Google Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash-lite"):
        """Initialize Gemini service.
        
        Args:
            api_key: Gemini API key. If None, will try to get from environment
            model_name: Gemini model name to use
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable must be set")
        
        self.client = genai.Client(api_key=self.api_key)
    
    def generate_response(
        self, 
        system_prompt: str, 
        user_input: str, 
        context: Optional[SessionContext] = None
    ) -> str:
        """Generate response from Gemini.
        
        Args:
            system_prompt: System prompt for the model
            user_input: User input text
            context: Optional session context
            
        Returns:
            Generated response text
        """
        # Construct the full prompt
        user_message = self._construct_user_message(user_input, context)
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                )
            )
            return response.text
        except Exception as e:
            return f"Error calling Gemini API: {str(e)}"
    
    def _construct_user_message(
        self,
        user_input: str,
        context: Optional[SessionContext] = None
    ) -> str:
        """Construct the user message, incorporating context.
        
        Args:
            user_input: User input
            context: Session context

        Returns:
            Constructed user message
        """
        parts = []

        # Add context information if available
        if context and context.resume_data:
            parts.append("Context: Resume data is available for analysis.")

        if context and context.job_description:
            parts.append(f"Job Description: {context.job_description}")

        parts.append(user_input)

        return "\n\n".join(parts)


class GeminiLiveService:
    """Service for Gemini Live API with audio support (placeholder implementation)."""
    
    def __init__(self):
        """Initialize Gemini Live service."""
        self.connected = False
        self.api_key = None
        self.model_name = None
        self.client = None
    
    def connect(self, api_key: str, model_name: str = "gemini-2.5-flash-native-audio-preview-12-2025") -> None:
        """Connect to Gemini Live API.
        
        Args:
            api_key: Gemini API key
            model_name: Model name for live interactions
        """
        try:
            self.api_key = api_key
            self.model_name = model_name
            self.client = genai.Client(api_key=api_key)
            self.connected = True
        except Exception as e:
            self.connected = False
            raise Exception(f"Failed to connect to Gemini Live: {str(e)}")
    
    def send_textAndWaitResponse(self, text: str, timeout_ms: int = 10000) -> Optional[str]:
        """Send text and wait for response.
        
        Args:
            text: Text to send
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Response text or None if timeout/error
        """
        if not self.connected or not self.client:
            return None
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=text,
            )
            return response.text
        except Exception as e:
            return f"Error in Gemini Live: {str(e)}"