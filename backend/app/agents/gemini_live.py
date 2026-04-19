import asyncio
import inspect
import logging

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiLive:
    """
    Handles the interaction with the Gemini Live API, acting as a relay.
    Ported from the gemini-live-genai-python-sdk example.
    """

    def __init__(
        self,
        api_key,
        model,
        input_sample_rate=16000,
        tools=None,
        tool_mapping=None,
        system_instruction=None,
    ):
        """
        Initializes the GeminiLive client.

        Args:
            api_key (str): The Gemini API Key.
            model (str): The model name to use.
            input_sample_rate (int): The sample rate for audio input.
            tools (list, optional): List of tools to enable. Defaults to None.
            tool_mapping (dict, optional): Mapping of tool names to functions. Defaults to None.
            system_instruction (str, optional): Custom system instruction.
        """
        self.api_key = api_key
        self.model = model
        self.input_sample_rate = input_sample_rate
        self.client = genai.Client(api_key=api_key)
        self.tools = tools or []
        self.tool_mapping = tool_mapping or {}
        self.system_instruction = (
            system_instruction or "You are a helpful AI assistant."
        )

    def _create_session_config(self):
        """Create the configuration for Gemini Live session."""
        return types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
                )
            ),
            system_instruction=types.Content(
                parts=[types.Part(text=self.system_instruction)]
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            realtime_input_config=types.RealtimeInputConfig(
                turn_coverage="TURN_INCLUDES_ONLY_ACTIVITY",
            ),
            tools=self.tools,
        )

    async def _send_audio(self, session, audio_input_queue):
        """Send audio chunks to Gemini Live session."""
        try:
            while True:
                chunk = await audio_input_queue.get()
                await session.send_realtime_input(
                    audio=types.Blob(
                        data=chunk, mime_type=f"audio/pcm;rate={self.input_sample_rate}"
                    )
                )
        except asyncio.CancelledError:
            logger.debug("send_audio task cancelled")
            raise
        except Exception as e:
            logger.exception(f"send_audio error: {e}")

    async def _send_video(self, session, video_input_queue):
        """Send video chunks to Gemini Live session."""
        try:
            while True:
                chunk = await video_input_queue.get()
                logger.info(f"Sending video frame to Gemini: {len(chunk)} bytes")
                await session.send_realtime_input(
                    video=types.Blob(data=chunk, mime_type="image/jpeg")
                )
        except asyncio.CancelledError:
            logger.debug("send_video task cancelled")
            raise
        except Exception as e:
            logger.exception(f"send_video error: {e}")

    async def _send_text(self, session, text_input_queue):
        """Send text messages to Gemini Live session."""
        try:
            while True:
                text = await text_input_queue.get()
                logger.info(f"Sending text to Gemini: {text}")
                await session.send_realtime_input(text=text)
        except asyncio.CancelledError:
            logger.debug("send_text task cancelled")
            raise
        except Exception as e:
            logger.exception(f"send_text error: {e}")

    async def _send_controls(self, session, control_input_queue):
        """Send control messages to Gemini Live session."""
        if control_input_queue is None:
            return
        try:
            while True:
                control = await control_input_queue.get()
                if control == "audio_stream_end":
                    logger.info("Forwarding audio_stream_end to Gemini")
                    await session.send_realtime_input(audio_stream_end=True)
        except asyncio.CancelledError:
            logger.debug("send_controls task cancelled")
            raise
        except Exception as e:
            logger.exception(f"send_controls error: {e}")

    async def _handle_server_content(
        self,
        server_content,
        audio_output_callback,
        audio_interrupt_callback,
        event_queue,
    ):
        """Handle server content from Gemini Live response."""
        if not server_content:
            return

        await self._handle_model_turn(server_content, audio_output_callback)
        await self._handle_transcriptions(server_content, event_queue)
        await self._handle_turn_events(
            server_content, audio_interrupt_callback, event_queue
        )

    async def _handle_model_turn(self, server_content, audio_output_callback):
        """Handle model turn content."""
        if not server_content.model_turn:
            return

        for part in server_content.model_turn.parts:
            if part.inline_data:
                if inspect.iscoroutinefunction(audio_output_callback):
                    await audio_output_callback(part.inline_data.data)
                else:
                    audio_output_callback(part.inline_data.data)

    async def _handle_transcriptions(self, server_content, event_queue):
        """Handle input and output transcriptions."""
        if (
            server_content.input_transcription
            and server_content.input_transcription.text
        ):
            await event_queue.put(
                {"type": "user", "text": server_content.input_transcription.text}
            )

        if (
            server_content.output_transcription
            and server_content.output_transcription.text
        ):
            await event_queue.put(
                {"type": "gemini", "text": server_content.output_transcription.text}
            )

    async def _handle_turn_events(
        self, server_content, audio_interrupt_callback, event_queue
    ):
        """Handle turn completion and interruption events."""
        if server_content.turn_complete:
            await event_queue.put({"type": "turn_complete"})

        if server_content.interrupted:
            await self._handle_interrupt(audio_interrupt_callback, event_queue)

    async def _handle_interrupt(self, audio_interrupt_callback, event_queue):
        """Handle interruption from Gemini Live session."""
        if audio_interrupt_callback:
            if inspect.iscoroutinefunction(audio_interrupt_callback):
                await audio_interrupt_callback()
            else:
                audio_interrupt_callback()
        await event_queue.put({"type": "interrupted"})

    async def _handle_tool_call(self, tool_call, session, event_queue):
        """Handle tool calls from Gemini Live session."""
        if not tool_call:
            return

        function_responses = []
        for fc in tool_call.function_calls:
            func_name = fc.name
            args = fc.args or {}

            if func_name in self.tool_mapping:
                result = await self._execute_tool_function(func_name, args)
                function_responses.append(
                    types.FunctionResponse(
                        name=func_name, id=fc.id, response={"result": result}
                    )
                )
                await event_queue.put(
                    {
                        "type": "tool_call",
                        "name": func_name,
                        "args": args,
                        "result": result,
                    }
                )

        await session.send_tool_response(function_responses=function_responses)

    async def _execute_tool_function(self, func_name, args):
        """Execute a tool function and return the result."""
        try:
            tool_func = self.tool_mapping[func_name]
            if inspect.iscoroutinefunction(tool_func):
                result = await tool_func(**args)
            else:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None, lambda f=tool_func, a=args: f(**a)
                )
        except Exception as e:
            result = f"Error: {e}"
        return result

    async def _receive_loop(
        self, session, audio_output_callback, audio_interrupt_callback, event_queue
    ):
        """Main receive loop for Gemini Live session."""
        try:
            while True:
                async for response in session.receive():
                    logger.debug(f"Received response from Gemini: {response}")

                    if response.go_away:
                        logger.warning(
                            f"Received GoAway from Gemini: {response.go_away}"
                        )
                        await event_queue.put(
                            {
                                "type": "error",
                                "error": "Gemini session ended: GoAway received",
                            }
                        )

                    await self._handle_server_content(
                        response.server_content,
                        audio_output_callback,
                        audio_interrupt_callback,
                        event_queue,
                    )
                    await self._handle_tool_call(
                        response.tool_call, session, event_queue
                    )

                logger.debug(
                    "Gemini receive iterator completed, re-entering receive loop"
                )

        except asyncio.CancelledError:
            logger.debug("receive_loop task cancelled")
            raise
        except Exception as e:
            await self._handle_receive_error(e, event_queue)
        finally:
            logger.info("receive_loop exiting")
            await event_queue.put(None)

    async def _handle_receive_error(self, error, event_queue):
        """Handle errors in the receive loop."""
        err_msg = str(error)
        logger.error(f"receive_loop error: {type(error).__name__}: {err_msg}")
        if "Resource has been exhausted" in err_msg or "quota" in err_msg.lower():
            await event_queue.put(
                {
                    "type": "error",
                    "error": "AI Quota exhausted. Please wait a minute and try again.",
                }
            )
        else:
            await event_queue.put(
                {"type": "error", "error": f"{type(error).__name__}: {err_msg}"}
            )

    def _cleanup_tasks(self, tasks):
        """Cancel all running tasks."""
        logger.info("Cleaning up Gemini Live session tasks")
        for task in tasks:
            task.cancel()

    async def start_session(
        self,
        audio_input_queue,
        video_input_queue,
        text_input_queue,
        audio_output_callback,
        audio_interrupt_callback=None,
        control_input_queue=None,
    ):
        config = self._create_session_config()

        logger.info(f"Connecting to Gemini Live with model={self.model}")
        try:
            async with self.client.aio.live.connect(
                model=self.model, config=config
            ) as session:
                logger.info("Gemini Live session opened successfully")

                event_queue = asyncio.Queue()

                send_audio_task = asyncio.create_task(
                    self._send_audio(session, audio_input_queue)
                )
                send_video_task = asyncio.create_task(
                    self._send_video(session, video_input_queue)
                )
                send_text_task = asyncio.create_task(
                    self._send_text(session, text_input_queue)
                )
                send_controls_task = asyncio.create_task(
                    self._send_controls(session, control_input_queue)
                )
                receive_task = asyncio.create_task(
                    self._receive_loop(
                        session,
                        audio_output_callback,
                        audio_interrupt_callback,
                        event_queue,
                    )
                )

                tasks = [
                    send_audio_task,
                    send_video_task,
                    send_text_task,
                    send_controls_task,
                    receive_task,
                ]

                try:
                    await text_input_queue.put(
                        "Start the live mock interview now. Greet the candidate and ask the first question."
                    )

                    while True:
                        event = await event_queue.get()
                        if event is None:
                            break
                        yield event
                finally:
                    await self._cleanup_tasks(tasks)
        except Exception as e:
            logger.exception(f"Gemini Live session error: {type(e).__name__}: {e}")
            raise
        finally:
            logger.info("Gemini Live session closed")
