import asyncio
import base64
import json
from typing import Annotated

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.agents.gemini_live import GeminiLive
from app.api.v1.services import get_or_create_session_context
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()
LIVE_MODEL = "gemini-3.1-flash-live-preview"  # Or your preferred live model


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
    """WebSocket endpoint for Gemini Live interview using the relay pattern."""
    await websocket.accept()
    logger.info(f"[VOICE_BACKEND] WebSocket connection accepted for session {session_id}")

    user_id = "dev-user"
    try:
        context = get_or_create_session_context(session_id=session_id, user_id=user_id)
    except Exception as e:
        logger.error(f"Session context creation failed: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    # 1. Prepare System Instruction
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
        "Focus on one question at a time."
    )

    if context.resume_data:
        resume_context = context.resume_data if isinstance(context.resume_data, str) else json.dumps(context.resume_data, indent=2)
        system_instruction += f"\n\nCandidate Resume Context:\n{resume_context}"

    if context.job_description:
        system_instruction += f"\n\nTarget Job Description:\n{context.job_description}"

    # 2. Setup Queues and Callbacks
    audio_input_queue = asyncio.Queue()
    video_input_queue = asyncio.Queue()
    text_input_queue = asyncio.Queue()

    async def audio_output_callback(data):
        # Send raw audio bytes to frontend as expected by the example
        await websocket.send_bytes(data)

    async def audio_interrupt_callback():
        # Signal interruption to frontend
        await websocket.send_json({"type": "interrupted"})

    gemini_client = GeminiLive(
        api_key=settings.GEMINI_API_KEY, 
        model=LIVE_MODEL, 
        input_sample_rate=16000,
        system_instruction=system_instruction
    )

    async def receive_from_client():
        try:
            while True:
                message = await websocket.receive()

                if message.get("bytes"):
                    await audio_input_queue.put(message["bytes"])
                elif message.get("text"):
                    text = message["text"]
                    try:
                        payload = json.loads(text)
                        if isinstance(payload, dict):
                            if payload.get("type") == "image":
                                image_data = base64.b64decode(payload["data"])
                                await video_input_queue.put(image_data)
                                continue
                            if payload.get("type") == "text":
                                await text_input_queue.put(payload["text"])
                                continue
                    except json.JSONDecodeError:
                        pass
                    
                    # Fallback for plain text
                    await text_input_queue.put(text)
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")
        except Exception as e:
            logger.error(f"Error receiving from client: {e}")

    receive_task = asyncio.create_task(receive_from_client())

    async def run_session():
        async for event in gemini_client.start_session(
            audio_input_queue=audio_input_queue,
            video_input_queue=video_input_queue,
            text_input_queue=text_input_queue,
            audio_output_callback=audio_output_callback,
            audio_interrupt_callback=audio_interrupt_callback,
        ):
            if event:
                # Forward structured events (transcriptions, tool calls, errors)
                await websocket.send_json(event)

    try:
        await run_session()
    except Exception as e:
        logger.error(f"Error in Gemini session: {e}")
    finally:
        receive_task.cancel()
        try:
            await websocket.close()
        except:
            pass
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
