"""Gemini API service for agent interactions."""

import os
import json
import re
from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types
from ..models.session import SessionContext
from ..core.config import settings


class GeminiService:
    """Service for interacting with Google Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash-lite"):
        """Initialize Gemini service.
        
        Args:
            api_key: Gemini API key. If None, will use settings
            model_name: Gemini model name to use
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        
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

        # Include analysis from prior agents (if present) so downstream agents can build on it
        if context and getattr(context, "shared_memory", None):
            analysis_results = context.shared_memory.get("analysis_results")
            if isinstance(analysis_results, dict) and analysis_results:
                try:
                    parts.append(
                        f"Previous analysis results:\n{json.dumps(analysis_results, indent=2)}"
                    )
                except Exception:
                    # Fall back to stringified form if JSON serialization fails
                    parts.append(f"Previous analysis results: {analysis_results}")

            # Include any conversational history (e.g., interview chat) to keep continuity
            message_history = context.shared_memory.get("message_history")
            if isinstance(message_history, list) and message_history:
                try:
                    parts.append("Conversation history:")
                    for m in message_history:
                        role = m.get("role", "user")
                        text = m.get("text", "")
                        parts.append(f"[{role}] {text}")
                except Exception:
                    parts.append(f"Conversation history: {message_history}")

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
    
    def send_audio_and_wait_response(self, audio_data: bytes, system_prompt: str, mime_type: str = "audio/wav", text_prompt: str = "", timeout_ms: int = 10000) -> Optional[str]:
        """Send audio data and wait for response.
        
        Args:
            audio_data: Audio data as bytes
            system_prompt: System prompt for the model
            mime_type: MIME type of the audio (default: audio/wav)
            text_prompt: Optional text prompt to accompany audio
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Response text or None if error
        """
        if not self.connected or not self.client:
            return None
        
        try:
            from google.genai import types
            audio_part = types.Part.from_bytes(data=audio_data, mime_type=mime_type)
            contents = [audio_part]
            if text_prompt:
                contents.insert(0, text_prompt)
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                )
            )
            return response.text
        except Exception as e:
            return f"Error in Gemini Live Audio: {str(e)}"