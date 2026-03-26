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
        "You are an expert Interview Coach. This is a LIVE voice interview. "
        "Speak naturally. Be encouraging. Ask one question at a time. "
        "Your goal is to simulate a real interview based on the user's resume and job description.\n\n"
        "PROACTIVE GREETING RULE:\n"
        "Immediately greet the candidate, reference the specific role they are applying for, "
        "and ask the FIRST targeted interview question. Do NOT wait for the user to speak first. "
        "Start the conversation yourself NOW."
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
            await session.send(
                input=types.LiveClientContent(parts=[types.Part.from_text(text="START_INTERVIEW_NOW")]),
                end_of_turn=True
            )
            
            async def send_to_client():
                """Relay audio from Gemini to Frontend."""
                try:
                    async for message in session.receive():
                        if message.server_content and message.server_content.model_turn:
                            parts = message.server_content.model_turn.parts
                            for part in parts:
                                if part.inline_data:
                                    # Send raw audio bytes to frontend
                                    await websocket.send_bytes(part.inline_data.data)
                                elif part.text:
                                    # Send text transcription if available
                                    await websocket.send_json({"text": part.text})
                        
                        if message.server_content and message.server_content.turn_complete:
                            await websocket.send_json({"event": "turn_complete"})
                            
                except Exception as e:
                    logger.error(f"Error receiving from Gemini: {e}")

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
                            # Send text command to Gemini
                            msg = json.loads(data["text"])
                            if msg.get("event") == "end_of_turn":
                                await session.send(input=types.LiveClientContent(parts=[]), end_of_turn=True)
                            elif msg.get("text"):
                                await session.send(
                                    input=types.LiveClientContent(parts=[types.Part.from_text(text=msg["text"])]),
                                    end_of_turn=True
                                )
                except WebSocketDisconnect:
                    raise
                except Exception as e:
                    logger.error(f"Error receiving from Client: {e}")

            # Run both relay loops
            await asyncio.gather(send_to_client(), receive_from_client())

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close()
