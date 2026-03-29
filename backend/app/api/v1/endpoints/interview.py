import asyncio
import base64
import json
import time
from typing import Annotated

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from google import genai
from google.genai import types

from app.api.v1.services import get_or_create_session_context
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()
LIVE_MODEL = "gemini-3.1-flash-live-preview"


@router.get("/token")
async def get_live_token(
    session_id: str,
):
    """Generate an ephemeral token for the frontend to connect directly to Gemini Live."""
    # Note: Ephemeral tokens are a security best practice for client-side direct connections.
    # In a production environment, you would use your service account to call Google's token endpoint.
    # For now, we will return the configuration and a flag to the frontend to use its own initialization.
    
    user_id = "dev-user"
    context = get_or_create_session_context(session_id=session_id, user_id=user_id)
    
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
        resume_context = context.resume_data
        if isinstance(resume_context, dict):
            resume_context = json.dumps(resume_context, indent=2)
        system_instruction += f"\n\nCandidate Resume Context:\n{resume_context}"

    if context.job_description:
        system_instruction += f"\n\nTarget Job Description:\n{context.job_description}"

    if not context.resume_data and not context.job_description:
        system_instruction += (
            "\n\nDIAGNOSTIC MODE: This is a system connectivity test. "
            "Greet the user warmly, confirm you are 'InterviewReady AI', and ask them how their day is going. "
            "Keep the response very short and friendly."
        )

    return {
        "api_key": settings.GEMINI_API_KEY, # In a real prod app, use Ephemeral Token instead
        "model": LIVE_MODEL,
        "system_instruction": system_instruction
    }


@router.websocket("/live")
async def interview_live_websocket(
    websocket: WebSocket,
    session_id: Annotated[str, Query(alias="sessionId")],
):
    """Handle a real-time Multimodal Live interview session with Gemini."""

    # ACCEPT immediately to prevent 403 Forbidden handshake rejections from FastAPI/Uvicorn
    await websocket.accept()
    logger.info(f"[VOICE_BACKEND] WebSocket accepted for session {session_id}")

    user_id = "dev-user"

    try:
        # Use get_or_create to support immediate testing/troubleshooting without prior upload
        context = get_or_create_session_context(session_id=session_id, user_id=user_id)
    except Exception as e:
        logger.error(f"Session context creation failed for {session_id}: {e}")
        await websocket.send_json({"error": f"Internal session error: {str(e)}"})
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    if not context:
        await websocket.send_json({"error": "Failed to initialize session"})
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return
    await websocket.send_json(
        {
            "type": "textStream",
            "data": "Connecting to AI Coach... Please wait a moment.",
        }
    )

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

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
        resume_context = context.resume_data
        if isinstance(resume_context, dict):
            resume_context = json.dumps(resume_context, indent=2)
        system_instruction += f"\n\nCandidate Resume Context:\n{resume_context}"

    if context.job_description:
        system_instruction += f"\n\nTarget Job Description:\n{context.job_description}"

    # If this is a diagnostic/empty session, adjust the prompt for a simple link test
    if not context.resume_data and not context.job_description:
        system_instruction += (
            "\n\nDIAGNOSTIC MODE: This is a system connectivity test. "
            "Greet the user warmly, confirm you are 'InterviewReady AI', and ask them how their day is going. "
            "Keep the response very short and friendly."
        )

    logger.info(
        f"Starting Live Interview for session {session_id}. "
        f"System instruction length: {len(system_instruction)}"
    )

    try:
        system_instruction_content = types.Content(
            parts=[types.Part(text=system_instruction)]
        )

        async with client.aio.live.connect(
            model=LIVE_MODEL,
            config=types.LiveConnectConfig(
                system_instruction=system_instruction_content,
                response_modalities=[types.Modality.AUDIO],
                speech_config=types.SpeechConfig(
                    language_code="en-US",
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Aoede"
                        )
                    ),
                ),
            ),
        ) as session:
            await websocket.send_json(
                {
                    "type": "textStream",
                    "data": "Voice session active. AI is initializing...",
                }
            )

            awaiting_model_response = True
            user_turn_state = {
                "id": 0,
                "chunks": 0,
                "bytes": 0,
                "started_at": None,
                "input_transcriptions": 0,
            }
            await session.send_realtime_input(
                text=(
                    "Start the live mock interview now. "
                    "Greet the candidate, mention the role, and ask the first question."
                )
            )

            async def send_to_client() -> None:
                """Relay Gemini events back to the browser websocket."""

                chunk_count = 0
                nonlocal awaiting_model_response, user_turn_state

                try:
                    async for response in session.receive():
                        # Log the raw event for debugging
                        logger.debug(f"[GEMINI_RAW_EVENT] {response}")

                        try:
                            content = response.server_content
                            if not content:
                                # Check for go_away even if content is missing
                                if response.go_away:
                                    logger.warning(f"Session closing in {response.go_away.time_left}")
                                    await websocket.send_json({
                                        "type": "warning",
                                        "data": f"Session will terminate in {response.go_away.time_left} due to connection limits."
                                    })
                                continue

                            # 1. Handle Interruption (Highest Priority)
                            if getattr(content, "interrupted", False):
                                logger.info("[VOICE_BACKEND] AI interrupted by user")
                                awaiting_model_response = False
                                await websocket.send_json({"interrupted": True})

                            # 3. Handle Model Turn (AI Audio only)
                            if getattr(content, "model_turn", None):
                                awaiting_model_response = True
                                for part in content.model_turn.parts:
                                    # Audio Data
                                    if getattr(part, "inline_data", None):
                                        audio_data = part.inline_data.data
                                        chunk_count += 1
                                        if chunk_count % 50 == 0:
                                            logger.info(f"[VOICE_TELEMETRY] Relaying AI audio chunk #{chunk_count}")
                                        
                                        encoded_audio = base64.b64encode(audio_data).decode("utf-8")
                                        await websocket.send_json({
                                            "type": "audioStream",
                                            "data": encoded_audio,
                                        })

                            # 5. Handle Turn Completion Signals
                            if getattr(content, "turn_complete", False) or getattr(content, "generation_complete", False):
                                logger.info("[VOICE_BACKEND] Turn/Generation Complete signal")
                                awaiting_model_response = False
                                await websocket.send_json({"event": "turn_complete"})

                            if response.go_away:
                                await websocket.send_json({
                                    "type": "warning",
                                    "data": f"Session will terminate in {response.go_away.time_left} due to connection limits.",
                                })
                        except Exception as inner_e:
                            logger.error(
                                f"Error processing Gemini message part: {inner_e}"
                            )
                except Exception as e:
                    logger.error(f"Gemini receive error: {e}")
                    await websocket.send_json({"error": str(e)})

            async def receive_from_client() -> None:
                """Relay browser audio/control messages to Gemini."""

                chunk_in_count = 0
                nonlocal awaiting_model_response, user_turn_state

                try:
                    while True:
                        data = await websocket.receive()

                        if data.get("bytes"):
                            awaiting_model_response = False
                            audio_bytes = data["bytes"]
                            chunk_in_count += 1
                            if user_turn_state["chunks"] == 0:
                                user_turn_state["id"] += 1
                                user_turn_state["started_at"] = time.monotonic()
                                logger.info(
                                    "[VOICE_BACKEND] Starting user audio turn "
                                    f"#{user_turn_state['id']}"
                                )
                            user_turn_state["chunks"] += 1
                            user_turn_state["bytes"] += len(audio_bytes)
                            if chunk_in_count % 50 == 0:
                                logger.debug(
                                    "[VOICE_BACKEND] Relaying chunk "
                                    f"#{chunk_in_count} ({len(audio_bytes)} bytes) to Gemini"
                                )

                            await session.send_realtime_input(
                                audio=types.Blob(
                                    data=audio_bytes,
                                    mime_type="audio/pcm;rate=16000",
                                )
                            )
                            continue

                        if not data.get("text"):
                            continue

                        try:
                            msg = json.loads(data["text"])
                        except json.JSONDecodeError:
                            continue

                        event_type = msg.get("event") or msg.get("type")

                        if msg.get("type") == "realtimeInput" and msg.get("audioData"):
                            audio_bytes = base64.b64decode(msg["audioData"])
                            awaiting_model_response = False
                            if user_turn_state["chunks"] == 0:
                                user_turn_state["id"] += 1
                                user_turn_state["started_at"] = time.monotonic()
                                logger.info(
                                    "[VOICE_BACKEND] Starting user audio turn "
                                    f"#{user_turn_state['id']} (base64 payload)"
                                )
                            user_turn_state["chunks"] += 1
                            user_turn_state["bytes"] += len(audio_bytes)
                            await session.send_realtime_input(
                                audio=types.Blob(
                                    data=audio_bytes,
                                    mime_type="audio/pcm;rate=16000",
                                )
                            )
                            continue

                        if event_type == "interrupt":
                            logger.info("[VOICE_BACKEND] Interrupt received")
                            awaiting_model_response = False
                            # Gemini Live 3.1 handles interruption through incoming
                            # realtime audio and server-side VAD. The client uses this
                            # event only as a local synchronization signal.
                            continue

                        if event_type == "audio_stream_end":
                            duration_ms = None
                            if user_turn_state["started_at"] is not None:
                                duration_ms = int(
                                    (time.monotonic() - user_turn_state["started_at"]) * 1000
                                )
                            logger.info(
                                "[VOICE_BACKEND] Audio stream end received "
                                f"for turn #{user_turn_state['id']} "
                                f"(chunks={user_turn_state['chunks']}, "
                                f"bytes={user_turn_state['bytes']}, "
                                f"input_transcriptions={user_turn_state['input_transcriptions']}, "
                                f"duration_ms={duration_ms})"
                            )
                            awaiting_model_response = True
                            # Force a response by sending turnComplete. Using send() directly as it's the correct way 
                            # to trigger a response if audio_stream_end alone fails.
                            try:
                                await session.send(types.LiveClientContent(turn_complete=True))
                            except Exception as e:
                                logger.error(f"Error sending turn_complete: {e}")
                                # Fallback to standard audio_stream_end if the new SDK method fails
                                await session.send_realtime_input(audio_stream_end=True)
                            
                            user_turn_state = {
                                "id": user_turn_state["id"],
                                "chunks": 0,
                                "bytes": 0,
                                "started_at": None,
                                "input_transcriptions": 0,
                            }
                            continue

                        if event_type == "ping":
                            await websocket.send_json({"event": "pong"})
                            continue

                        if msg.get("text"):
                            awaiting_model_response = False
                            await session.send_realtime_input(text=msg["text"])
                except WebSocketDisconnect:
                    logger.info(f"Client disconnected for session {session_id}")
                    raise
                except Exception as e:
                    logger.error(f"Error receiving from Client: {e}")
                    await websocket.send_json(
                        {"error": f"Client communication error: {str(e)}"}
                    )

            async with asyncio.TaskGroup() as tg:
                tg.create_task(send_to_client())
                tg.create_task(receive_from_client())

            logger.info(f"WebSocket disconnected for session {session_id}")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
        if websocket.client_state.name != "DISCONNECTED":
            try:
                await websocket.send_json({"error": f"Voice session failed: {str(e)}"})
            except Exception:
                pass
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Voice session failed")
