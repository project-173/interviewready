import asyncio
import base64
import json
import traceback
from typing import Annotated

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.agents.gemini_live import GeminiLive
from app.api.v1.services import get_or_create_session_context
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()
LIVE_MODEL = "gemini-3.1-flash-live-preview"


def _build_system_instruction(context) -> str:
    system_instruction = (
        "You are an expert Interview Coach conducting a LIVE VOICE mock interview. "
        "IMPORTANT: You must speak naturally, warmly, and concisely. "
        "Your goal is to simulate a professional interview based on the user's "
        "resume and the job description provided.\n\n"
        "MANDATORY STARTUP RULE:\n"
        "1. Immediately start the conversation yourself. Do NOT wait for a 'hello' from the user.\n"
        "2. Begin with a professional greeting.\n"
        "3. Explicitly state the role you are interviewing them for.\n"
        "4. Ask the first targeted interview question right away.\n"
        "5. Keep your responses short to allow for a back-and-forth flow.\n\n"
        "Focus on one question at a time."
    )

    if getattr(context, "resume_data", None):
        resume_context = context.resume_data
        if isinstance(resume_context, dict):
            resume_context = json.dumps(resume_context, indent=2)
        system_instruction += f"\n\nCandidate Resume Context:\n{resume_context}"

    if getattr(context, "job_description", None):
        system_instruction += (
            f"\n\nTarget Job Description:\n{context.job_description}"
        )

    if not getattr(context, "resume_data", None) and not getattr(
        context, "job_description", None
    ):
        system_instruction += (
            "\n\nDIAGNOSTIC MODE: This is a system connectivity test. "
            "Greet the user warmly, confirm you are InterviewReady AI, "
            "and ask a short opening question."
        )

    return system_instruction


@router.get("/token")
async def get_live_token(session_id: str):
    """Return current live-session config for the frontend relay flow."""
    user_id = "dev-user"
    context = get_or_create_session_context(session_id=session_id, user_id=user_id)

    return {
        "api_key": settings.GEMINI_API_KEY,
        "model": LIVE_MODEL,
        "system_instruction": _build_system_instruction(context),
    }


@router.websocket("/live")
async def interview_live_websocket(
    websocket: WebSocket,
    session_id: Annotated[str, Query(alias="sessionId")],
):
    """WebSocket relay between the browser and Gemini Live."""
    await websocket.accept()
    logger.info(
        f"[VOICE_BACKEND] WebSocket connection accepted for session {session_id}"
    )

    user_id = "dev-user"
    try:
        context = get_or_create_session_context(session_id=session_id, user_id=user_id)
    except Exception as exc:
        logger.error(f"[VOICE_BACKEND] Session context creation failed: {exc}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    await websocket.send_json(
        {
            "type": "textStream",
            "data": "Connecting to AI Coach... Please wait a moment.",
        }
    )

    audio_input_queue: asyncio.Queue[bytes] = asyncio.Queue()
    video_input_queue: asyncio.Queue[bytes] = asyncio.Queue()
    text_input_queue: asyncio.Queue[str] = asyncio.Queue()
    control_input_queue: asyncio.Queue[str] = asyncio.Queue()

    gemini_client = GeminiLive(
        api_key=settings.GEMINI_API_KEY,
        model=LIVE_MODEL,
        input_sample_rate=16000,
        system_instruction=_build_system_instruction(context),
    )

    async def audio_output_callback(data: bytes):
        await websocket.send_bytes(data)

    async def audio_interrupt_callback():
        await websocket.send_json({"type": "interrupted"})

    async def receive_from_client():
        try:
            while True:
                message = await websocket.receive()

                if message.get("bytes"):
                    await audio_input_queue.put(message["bytes"])
                    continue

                raw_text = message.get("text")
                if not raw_text:
                    continue

                try:
                    payload = json.loads(raw_text)
                except json.JSONDecodeError:
                    await text_input_queue.put(raw_text)
                    continue

                if not isinstance(payload, dict):
                    continue

                event_type = payload.get("event") or payload.get("type")

                if event_type == "ping":
                    await websocket.send_json({"event": "pong"})
                    continue

                if event_type == "interrupt":
                    logger.info("[VOICE_BACKEND] Interrupt received from frontend")
                    # Gemini Live handles true interruption from incoming audio.
                    await websocket.send_json({"type": "interrupted"})
                    continue

                if event_type == "audio_stream_end":
                    logger.info("[VOICE_BACKEND] Audio stream end received from frontend")
                    await control_input_queue.put("audio_stream_end")
                    continue

                if payload.get("audioData"):
                    await audio_input_queue.put(base64.b64decode(payload["audioData"]))
                    continue

                if payload.get("type") == "image" and payload.get("data"):
                    await video_input_queue.put(base64.b64decode(payload["data"]))
                    continue

                if payload.get("text"):
                    await text_input_queue.put(payload["text"])
        except WebSocketDisconnect:
            logger.info(f"[VOICE_BACKEND] Client disconnected for session {session_id}")
            raise
        except Exception as exc:
            if "disconnect message has been received" in str(exc):
                logger.info(
                    f"[VOICE_BACKEND] Client receive loop closed for session {session_id}"
                )
                raise WebSocketDisconnect
            logger.error(f"[VOICE_BACKEND] Error receiving from client: {exc}")
            await websocket.send_json(
                {"error": f"Client communication error: {str(exc)}"}
            )

    async def run_session():
        await websocket.send_json(
            {"type": "textStream", "data": "Voice session active. AI is initializing..."}
        )

        async for event in gemini_client.start_session(
            audio_input_queue=audio_input_queue,
            video_input_queue=video_input_queue,
            text_input_queue=text_input_queue,
            control_input_queue=control_input_queue,
            audio_output_callback=audio_output_callback,
            audio_interrupt_callback=audio_interrupt_callback,
        ):
            if not event:
                continue

            event_type = event.get("type")

            if event_type == "user":
                await websocket.send_json(
                    {"type": "inputTranscription", "data": event.get("text", "")}
                )
                continue

            if event_type == "gemini":
                await websocket.send_json(
                    {"type": "textStream", "data": event.get("text", "")}
                )
                continue

            if event_type == "turn_complete":
                await websocket.send_json({"type": "turn_complete"})
                continue

            if event_type == "interrupted":
                await websocket.send_json({"type": "interrupted"})
                continue

            if event_type == "error":
                await websocket.send_json({"error": event.get("error", "Unknown error")})
                continue

            await websocket.send_json(event)

    receive_task = asyncio.create_task(receive_from_client())

    try:
        await run_session()
    except asyncio.CancelledError:
        logger.info(f"[VOICE_BACKEND] Session task cancelled for session {session_id}")
    except WebSocketDisconnect:
        logger.info(f"[VOICE_BACKEND] WebSocket disconnected for session {session_id}")
    except Exception as exc:
        logger.error(f"[VOICE_BACKEND] WebSocket Error in session {session_id}: {type(exc).__name__}: {exc}")
        logger.error(traceback.format_exc())
        if websocket.client_state.name != "DISCONNECTED":
            try:
                await websocket.send_json({"error": f"Voice session failed: {str(exc)}"})
            except Exception:
                pass
            try:
                await websocket.close(
                    code=status.WS_1011_INTERNAL_ERROR, reason=f"Voice session error: {type(exc).__name__}"
                )
            except Exception:
                pass
    finally:
        receive_task.cancel()
        try:
            # Shield the cleanup to ensure it completes even if the main task is being cancelled
            await asyncio.shield(receive_task)
        except (asyncio.CancelledError, Exception):
            pass
        
        if websocket.client_state.name != "DISCONNECTED":
            try:
                logger.info(f"[VOICE_BACKEND] Closing WebSocket for session {session_id}")
                await websocket.close()
            except Exception as e:
                logger.debug(f"[VOICE_BACKEND] Error during final websocket close: {e}")
