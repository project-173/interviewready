import asyncio
import json
import base64
from typing import Annotated

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from google import genai
from google.genai import types

from app.api.v1.services import get_session_context
from app.core.config import settings
from app.core.logging import logger
from app.utils.audio_utils import pcm_to_wav

router = APIRouter()

@router.websocket("/live")
async def interview_live_websocket(
    websocket: WebSocket,
    session_id: Annotated[str, Query(alias="sessionId")],
):
    """Handle real-time Multimodal Live session with Gemini."""
    user_id = "dev-user"

    try:
        context = get_session_context(session_id=session_id, user_id=user_id)
    except Exception as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if not context:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    
    # IMMEDIATE ACK: Tell the frontend we're initializing to prevent timeout
    await websocket.send_json({"type": "textStream", "data": "Connecting to AI Coach... Please wait a moment."})
    
    # Initialize Gemini client
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    # Get initial interview instructions from the agent logic
    # (Simplified for the WebSocket version)
    system_instruction = (
        "You are an expert Interview Coach conducting a LIVE VOICE mock interview. "
        "IMPORTANT: You must speak naturally, warmly, and concisely. "
        "Your goal is to simulate a professional interview based on the user's resume and the job description provided.\n\n"
        "MANDATORY STARTUP RULE:\n"
        "1. Immediately start the conversation yourself. Do NOT wait for a 'hello' from the user.\n"
        "2. Begin with a professional greeting (e.g., 'Hello! Thanks for joining today.').\n"
        "3. Explicitly state the role you are interviewing them for.\n"
        "4. Ask the FIRST targeted interview question right away.\n"
        "5. Keep your responses short to allow for a back-and-forth flow.\n\n"
        "Focus on one question at a time. If the user stops talking, wait briefly but be ready to guide the conversation if needed."
    )

    if context.resume_data:
        # resume_data might be a string (raw text) or a dict (parsed resume)
        resume_context = context.resume_data
        if isinstance(resume_context, dict):
            resume_context = json.dumps(resume_context, indent=2)
        system_instruction += f"\n\nCandidate Resume Context:\n{resume_context}"

    if context.job_description:
        system_instruction += f"\n\nTarget Job Description:\n{context.job_description}"

    try:
        # Wrap system instruction correctly for LiveConnectConfig
        system_content = types.Content(parts=[types.Part.from_text(text=system_instruction)])

        # Connect to Gemini Multimodal Live
        # Use gemini-3.1-flash-live-preview as requested for voice
        async with client.aio.live.connect(
            model="gemini-3.1-flash-live-preview",
            config=types.LiveConnectConfig(
                system_instruction=system_content,
                response_modalities=[types.Modality.AUDIO],
                # Enable transcription for better UX
                output_audio_transcription=types.LiveConnectConfigOutputAudioTranscription(
                    enabled=True
                )
            )
        ) as session:
            # Send initial "ready" signal to frontend
            await websocket.send_json({"type": "textStream", "data": "\nSession Established. Waking up the coach..."})

            # WARM-UP DELAY: Give Gemini a moment to fully initialize its stream
            logger.info(f"Connected to Gemini 3.1 Live for {session_id}. Waiting for warm-up...")
            await asyncio.sleep(1.5) 
            
            # Use send_realtime_input as per SKILL.md best practices
            logger.info(f"Sending initial greeting trigger for {session_id}")
            await session.send_realtime_input(
                text="Please start the interview session now. Introduce yourself briefly, mention the specific role from the job description, and ask your first question."
            )
            
            async def send_to_client():
                """Relay audio from Gemini to Frontend."""
                try:
                    async for message in session.receive():
                        # Handle audio output transcription
                        if message.server_content and message.server_content.output_audio_transcription:
                            transcription = message.server_content.output_audio_transcription.text
                            if transcription:
                                await websocket.send_json({"type": "textStream", "data": transcription})

                        # Handle audio data
                        if message.server_content and message.server_content.model_turn:
                            parts = message.server_content.model_turn.parts
                            for part in parts:
                                if part.inline_data:
                                    # Send as structured JSON with base64 data to match sample code pattern
                                    # This is more reliable for handling multiple streams
                                    encoded_audio = base64.b64encode(part.inline_data.data).decode('utf-8')
                                    await websocket.send_json({"type": "audioStream", "data": encoded_audio})
                        
                        if message.server_content and message.server_content.turn_complete:
                            await websocket.send_json({"event": "turn_complete"})
                            
                except Exception as e:
                    logger.error(f"Error receiving from Gemini: {e}")
                    await websocket.send_json({"error": f"Gemini connection error: {str(e)}"})

            async def receive_from_client():
                """Relay audio/text from Frontend to Gemini."""
                try:
                    while True:
                        data = await websocket.receive()
                        
                        # Support both binary and JSON text formats
                        # Using session.send_realtime_input as recommended in SKILL.md
                        if "bytes" in data:
                            # Direct binary PCM
                            await session.send_realtime_input(
                                audio=types.Blob(data=data["bytes"], mime_type="audio/pcm;rate=16000")
                            )
                        elif "text" in data:
                            try:
                                msg = json.loads(data["text"])
                                # Handle sample-code style input
                                if msg.get("type") == "realtimeInput" and msg.get("audioData"):
                                    audio_bytes = base64.b64decode(msg["audioData"])
                                    await session.send_realtime_input(
                                        audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
                                    )
                                elif msg.get("type") == "contentUpdateText" and msg.get("text"):
                                    await session.send_realtime_input(text=msg["text"])
                                # Handle heartbeat
                                elif msg.get("event") == "ping":
                                    continue
                                # Legacy support
                                elif msg.get("text"):
                                    await session.send_realtime_input(text=msg["text"])
                            except json.JSONDecodeError:
                                logger.warning(f"Received non-JSON text from client: {data['text']}")
                except WebSocketDisconnect:
                    logger.info(f"Client disconnected for session {session_id}")
                    raise
                except Exception as e:
                    logger.error(f"Error receiving from Client: {e}")
                    await websocket.send_json({"error": f"Client communication error: {str(e)}"})

            # Run both relay loops
            await asyncio.gather(send_to_client(), receive_from_client())

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close()
