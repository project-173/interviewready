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

    logger.info(f"Starting Live Interview for session {session_id}. System instruction length: {len(system_instruction)}")

    try:
        # SKILL.md compliant config
        system_instruction_content = types.Content(
            parts=[types.Part(text=system_instruction)]
        )

        # Connect to Gemini Multimodal Live (using gemini-3.1-flash-live-preview)
        async with client.aio.live.connect(
            model="gemini-3.1-flash-live-preview",
            config=types.LiveConnectConfig(
                system_instruction=system_instruction_content,
                response_modalities=[types.Modality.AUDIO],
                # Enable context window compression for long interviews (>15m)
                context_window_compression=types.ContextWindowCompressionConfig(
                    sliding_window=types.SlidingWindow(),
                ),
            )
        ) as session:
            # Immediate feedback to frontend
            await websocket.send_json({"type": "textStream", "data": "Voice session active. AI is initializing..."})

            async def send_to_client():
                """Relay ALL parts of Gemini messages safely."""
                try:
                async for response in session.receive():
                    try:
                        content = response.server_content
                        if content:
                            # 1. Handle Interruption
                            if hasattr(content, 'interrupted') and content.interrupted:
                                logger.info(f"[VOICE_BACKEND] AI interrupted by user")
                                await websocket.send_json({"interrupted": True})
                            
                            # 2. Handle Audio Data
                            if hasattr(content, 'model_turn') and content.model_turn:
                                for part in content.model_turn.parts:
                                    if part.inline_data:
                                        audio_data = part.inline_data.data
                                        logger.debug(f"Received audio chunk from Gemini: {len(audio_data)} bytes")
                                        encoded_audio = base64.b64encode(audio_data).decode('utf-8')
                                        await websocket.send_json({"type": "audioStream", "data": encoded_audio})
                                    if part.text:
                                        # Some model turns might include text parts (rare in audio mode but possible)
                                        logger.info(f"[VOICE_BACKEND] AI Text Part: {part.text}")
                                        await websocket.send_json({"type": "textStream", "data": part.text})

                            # 3. Handle Transcription (Using correct SDK attribute names)
                            # The SDK uses 'input_transcription' and 'output_transcription'
                            if hasattr(content, 'input_transcription') and content.input_transcription:
                                logger.info(f"[VOICE_BACKEND] User Input Transcription: {content.input_transcription.text}")
                                await websocket.send_json({"type": "inputTranscription", "data": content.input_transcription.text})
                            
                            if hasattr(content, 'output_transcription') and content.output_transcription:
                                logger.info(f"[VOICE_BACKEND] AI Output Transcription: {content.output_transcription.text}")
                                await websocket.send_json({"type": "textStream", "data": content.output_transcription.text})
                            
                            # 4. Handle Turn Complete / Generation Complete
                            if hasattr(content, 'turn_complete') and content.turn_complete:
                                logger.info(f"[VOICE_BACKEND] Turn Complete signal received from Gemini")
                                await websocket.send_json({"event": "turn_complete"})
                            
                            if hasattr(content, 'generation_complete') and content.generation_complete:
                                logger.info(f"[VOICE_BACKEND] Generation Complete signal received from Gemini")
                                await websocket.send_json({"event": "generation_complete"})

                            # 5. Handle GoAway Signal (Session about to end)
                            if response.go_away:
                                await websocket.send_json({
                                    "type": "warning", 
                                    "data": f"Session will terminate in {response.go_away.time_left} due to connection limits."
                                })
                        except Exception as inner_e:
                            logger.error(f"Error processing Gemini message part: {inner_e}")
                            # Don't crash the whole session if one part fails
                            
                except Exception as e:
                    logger.error(f"Gemini receive error: {e}")
                    await websocket.send_json({"error": str(e)})

            async def receive_from_client():
                """Relay audio/text from Frontend to Gemini using send_realtime_input."""
                try:
                    while True:
                        data = await websocket.receive()
                        
                        if "bytes" in data:
                            # SKILL.md: Send audio using the 'audio' key in send_realtime_input
                            logger.info(f"[VOICE_BACKEND] Relaying raw bytes from client: {len(data['bytes'])} bytes")
                            await session.send_realtime_input(
                                audio=types.Blob(data=data["bytes"], mime_type="audio/pcm;rate=16000")
                            )
                        elif "text" in data:
                            try:
                                msg = json.loads(data["text"])
                                if msg.get("type") == "realtimeInput" and msg.get("audioData"):
                                    audio_bytes = base64.b64decode(msg["audioData"])
                                    logger.info(f"[VOICE_BACKEND] Relaying base64 audio from client: {len(audio_bytes)} bytes")
                                    await session.send_realtime_input(
                                        audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
                                    )
                                elif msg.get("type") == "contentUpdateText" and msg.get("text"):
                                    await session.send_realtime_input(text=msg["text"])
                                elif msg.get("event") == "ping":
                                    await websocket.send_json({"event": "pong"})
                                    continue
                                elif msg.get("text"):
                                    await session.send_realtime_input(text=msg["text"])
                            except json.JSONDecodeError:
                                pass
                except WebSocketDisconnect:
                    logger.info(f"Client disconnected for session {session_id}")
                    raise
                except Exception as e:
                    logger.error(f"Error receiving from Client: {e}")
                    await websocket.send_json({"error": f"Client communication error: {str(e)}"})

            # Run both relay loops using TaskGroup for robustness
            async with asyncio.TaskGroup() as tg:
                tg.create_task(send_to_client())
                tg.create_task(receive_from_client())

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close()
