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
        async with client.aio.models.connect(
            model=settings.GEMINI_MODEL,
            config=types.LiveConnectConfig(
                system_instruction=system_content,
                response_modalities=[types.LiveClientRealtimeInputMessageRealtimeClientContentRealtimeInputMessageRealtimeClientContentResponseModalities.AUDIO],
            )
        ) as session:
            # Send an initial message formatted properly to trigger the proactive greeting
            # Using a more explicit command and ensuring end_of_turn=True
            logger.info(f"Starting Gemini Live session for {session_id}")
            await session.send(
                input=types.LiveClientContent(parts=[types.Part.from_text(text="START_INTERVIEW_SESSION: Greet me and ask the first question.")]),
                end_of_turn=True
            )
            
            async def send_to_client():
                """Relay audio from Gemini to Frontend."""
                try:
                    async for message in session.receive():
                        if message.server_content:
                            if message.server_content.model_turn:
                                parts = message.server_content.model_turn.parts
                                for part in parts:
                                    if part.inline_data:
                                        # Wrap raw PCM in WAV header for browser compatibility
                                        wav_data = pcm_to_wav(part.inline_data.data, sample_rate=24000)
                                        await websocket.send_bytes(wav_data)
                                    elif part.text:
                                        # Send text transcription if available
                                        await websocket.send_json({"text": part.text})
                            
                            if message.server_content.turn_complete:
                                await websocket.send_json({"event": "turn_complete"})
                            
                except Exception as e:
                    logger.error(f"Error receiving from Gemini: {e}")
                    await websocket.send_json({"error": f"Gemini connection error: {str(e)}"})

            async def receive_from_client():
                """Relay audio/text from Frontend to Gemini."""
                try:
                    while True:
                        data = await websocket.receive()
                        if "bytes" in data:
                            # Send raw audio to Gemini with correct sample rate MIME type
                            await session.send(
                                input=types.LiveClientContent(
                                    parts=[types.Part.from_bytes(data=data["bytes"], mime_type="audio/pcm;rate=16000")]
                                ),
                                end_of_turn=False # VAD handled by Gemini or Frontend
                            )
                        elif "text" in data:
                            # Send text command or heartbeat to Gemini
                            try:
                                msg = json.loads(data["text"])
                                if msg.get("event") == "ping":
                                    # Just a heartbeat, no need to forward to Gemini unless we want to keep IT alive too
                                    continue
                                elif msg.get("event") == "end_of_turn":
                                    await session.send(input=types.LiveClientContent(parts=[]), end_of_turn=True)
                                elif msg.get("text"):
                                    await session.send(
                                        input=types.LiveClientContent(parts=[types.Part.from_text(text=msg["text"])]),
                                        end_of_turn=True
                                    )
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
