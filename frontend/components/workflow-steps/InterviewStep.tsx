import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { InterviewMessage, InterviewMode } from '../../types';

// Custom hook for WebSocket setup to reduce cognitive complexity
const useWebSocketConnection = (
  mode: InterviewMode,
  sessionId: string,
  onLiveEvent?: (event: { type: string; text?: string }) => void,
  callbacks?: {
    onAudioData: (data: Float32Array<ArrayBuffer>) => void;
    onInterrupted: () => void;
    onTurnComplete: () => void;
    onConnectionChange: (status: "connecting" | "connected" | "error" | "closed") => void;
  }
) => {
  const socketRef = useRef<WebSocket | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<
    "connecting" | "connected" | "error" | "closed"
  >("connecting");
  const heartbeatIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (mode !== "VOICE") return;

    let isComponentMounted = true;
    const protocol =
      globalThis.location.protocol === "https:" ? "wss:" : "ws:";
    const API_BASE_URL =
      import.meta.env.VITE_API_BASE_URL || globalThis.location.origin;

    const hostAndPath = API_BASE_URL.replace(/^https?:\/\//, "").replace(
      /\/$/,
      ""
    );
    const wsUrl = `${protocol}//${hostAndPath}/api/v1/interview/live?sessionId=${sessionId}`;

    const initializeRelaySession = async () => {
      try {
        console.log(
          "[VOICE_FRONTEND] Connecting to Backend Relay WebSocket..."
        );
        const ws = new WebSocket(wsUrl);
        ws.binaryType = "arraybuffer";
        socketRef.current = ws;

        ws.onopen = () => {
          if (!isComponentMounted) return;
          console.log("[VOICE_FRONTEND] Relay Connection Established");
          setConnectionStatus("connected");
          callbacks?.onConnectionChange("connected");

          if (heartbeatIntervalRef.current)
            clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ event: "ping", type: "control" }));
            }
          }, 25000);
        };

        ws.onmessage = (event) => {
          if (!isComponentMounted) return;

          if (event.data instanceof ArrayBuffer) {
            const binary = event.data;
            const dataView = new DataView(binary);
            const float32: Float32Array<ArrayBuffer> = new Float32Array(
              binary.byteLength / 2
            );
            for (let i = 0; i < float32.length; i++) {
              float32[i] = dataView.getInt16(i * 2, true) / 32768;
            }
            callbacks?.onAudioData(float32);
          } else if (typeof event.data === "string") {
            try {
              const msg = JSON.parse(event.data);

              if (msg.type === "interrupted") {
                console.log("[VOICE_FRONTEND] Interruption signal from relay");
                callbacks?.onInterrupted();
              }

              if (msg.type === "turn_complete") {
                callbacks?.onTurnComplete();
              }

              if (onLiveEvent) {
                onLiveEvent(msg);
              }
            } catch (e) {
              console.error("Relay message parse error:", e);
            }
          }
        };

        ws.onerror = (error) => {
          console.error("[VOICE_FRONTEND] Relay WebSocket Error:", error);
          setConnectionStatus("error");
          callbacks?.onConnectionChange("error");
        };

        ws.onclose = (event) => {
          console.log(
            `[VOICE_FRONTEND] Relay Connection Closed (Code: ${event.code}, Reason: ${event.reason || "none"})`
          );
          setConnectionStatus("closed");
          callbacks?.onConnectionChange("closed");
          if (heartbeatIntervalRef.current) {
            clearInterval(heartbeatIntervalRef.current);
            heartbeatIntervalRef.current = null;
          }
        };
      } catch (err) {
        console.error("[VOICE_FRONTEND] Relay initialization failed:", err);
        setConnectionStatus("error");
        callbacks?.onConnectionChange("error");
      }
    };

    initializeRelaySession();

    return () => {
      isComponentMounted = false;
      if (socketRef.current) {
        socketRef.current.close();
      }
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
      }
    };
  }, [mode, sessionId, callbacks, onLiveEvent]);

  return { socketRef, connectionStatus };
};

// Extracted markdown components to reduce inline definitions
const markdownComponents = {
  p: ({ children }: { children: React.ReactNode }) => (
    <p className="mb-2 last:mb-0">{children}</p>
  ),
  ul: ({ children }: { children: React.ReactNode }) => (
    <ul className="list-disc pl-4 mb-2">{children}</ul>
  ),
  li: ({ children }: { children: React.ReactNode }) => (
    <li className="mb-0.5">{children}</li>
  ),
  strong: ({ children }: { children: React.ReactNode }) => (
    <span className="font-bold">{children}</span>
  ),
};

export const InterviewStep: React.FC<{ 
	  history: InterviewMessage[]; 
	  onSend: (msg: string) => void;
	  onSendAudio: (audio: Uint8Array) => void;
	  isLoading: boolean;
	  isComplete?: boolean;
	  chatEndRef: React.RefObject<HTMLDivElement | null>;
	  mode: InterviewMode;
	  sessionId: string;
	  onExit?: () => void;
	  onLiveEvent?: (event: { type: string; text?: string }) => void;
	}> = ({
  history,
  onSend,
  onSendAudio,
  isLoading,
  isComplete = false,
  chatEndRef,
  mode,
  sessionId,
  onExit,
  onLiveEvent,
}) => {
  const [message, setMessage] = React.useState("");
  const [isRecording, setIsRecording] = React.useState(false);
  const [isSpeaking, setIsSpeaking] = React.useState(false);
  const [isVoiceActive, setIsVoiceActive] = React.useState(false);
  const audioChunksRef = React.useRef<Float32Array[]>([]);
  const playbackQueueRef = React.useRef<Float32Array<ArrayBuffer>[]>([]);
  const isQueueProcessingRef = React.useRef(false);
  const nextStartTimeRef = React.useRef(0);
  const animationFrameRef = React.useRef<number | null>(null);
  const silenceTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const resumeListeningTimeoutRef = React.useRef<
    ReturnType<typeof setTimeout> | null
  >(null);
  const isSendingAudioRef = React.useRef(true);

  // Refs to track current state inside stale closures (WebSocket handlers, timers, VAD)
  const aiTurnActiveRef = React.useRef(false);
  const isSpeakingRef = React.useRef(false);
  const isVoiceActiveRef = React.useRef(false);
  const isRecordingRef = React.useRef(false);
  const isStartingRecordingRef = React.useRef(false);
  const hasDetectedSpeechRef = React.useRef(false);
  const recordingAttemptRef = React.useRef(0);
  const mediaStreamRef = React.useRef<MediaStream | null>(null);
  const processorRef = React.useRef<AudioWorkletNode | null>(null);
  // Single shared AudioContext for playback â€” avoids creating a new one per audio chunk
  const playbackContextRef = React.useRef<AudioContext | null>(null);
  const activePlaybackSourcesRef = React.useRef<Set<AudioBufferSourceNode>>(
    new Set(),
  );
  // Separate AudioContext for microphone capture
  const recordingContextRef = React.useRef<AudioContext | null>(null);
  // Tracks if the worklet module is registered for the recording context
  const workletRegisteredRef = React.useRef<boolean>(false);

  // Keep refs in sync with state so closures always have fresh values
  React.useEffect(() => {
    isSpeakingRef.current = isSpeaking;
  }, [isSpeaking]);

  React.useEffect(() => {
    isRecordingRef.current = isRecording;
  }, [isRecording]);

  React.useEffect(() => {
    isVoiceActiveRef.current = isVoiceActive;
  }, [isVoiceActive]);

  const stopPlaybackImmediately = () => {
    playbackQueueRef.current = [];
    nextStartTimeRef.current = 0;
    isQueueProcessingRef.current = false;

    activePlaybackSourcesRef.current.forEach((source) => {
      try {
        source.onended = null;
        source.stop();
      } catch {
        // Ignore already-ended sources during interruption cleanup.
      }
      try {
        source.disconnect();
      } catch {
        // Ignore disconnect races during teardown.
      }
    });
    activePlaybackSourcesRef.current.clear();

    isSpeakingRef.current = false;
    setIsSpeaking(false);
  };

  const queueResumeListening = (delayMs = 250) => {
    if (resumeListeningTimeoutRef.current) {
      globalThis.clearTimeout(resumeListeningTimeoutRef.current);
      resumeListeningTimeoutRef.current = null;
    }

    resumeListeningTimeoutRef.current = globalThis.setTimeout(() => {
      resumeListeningTimeoutRef.current = null;
      if (
        mode === "VOICE" &&
        socketRef.current?.readyState === WebSocket.OPEN &&
        !isSpeakingRef.current &&
        !isRecordingRef.current &&
        !isStartingRecordingRef.current &&
        !aiTurnActiveRef.current
      ) {
        startRecording().catch((error) => {
          console.error("[VOICE_FRONTEND] Failed to resume listening:", error);
        });
      }
    }, delayMs);
  };

  const teardownRecording = (notifyBackend: boolean) => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }

    const currentProcessor = processorRef.current;
    const currentStream = mediaStreamRef.current;
    const shouldSignalAudioEnd = notifyBackend && hasDetectedSpeechRef.current;

    processorRef.current = null;
    mediaStreamRef.current = null;
    isRecordingRef.current = false;
    isStartingRecordingRef.current = false;
    isSendingAudioRef.current = false;
    hasDetectedSpeechRef.current = false;
    isVoiceActiveRef.current = false;
    recordingAttemptRef.current += 1;
    setIsRecording(false);
    setIsVoiceActive(false);

    if (currentProcessor) {
      currentProcessor.disconnect();
    }
    if (currentStream) {
      currentStream.getTracks().forEach((track) => track.stop());
    }

    if (
      shouldSignalAudioEnd &&
      mode === "VOICE" &&
      socketRef.current?.readyState === WebSocket.OPEN
    ) {
      console.log("[VOICE_FRONTEND] Signaling audio stream end to backend");
      socketRef.current.send(
        JSON.stringify({ type: "realtimeInput", event: "audio_stream_end" }),
      );
    }

    if (mode === "CHAT" && audioChunksRef.current.length > 0) {
      console.log("Processing legacy audio buffer for CHAT mode");
      const sampleRate = 16000;
      const allSamples: number[] = [];
      audioChunksRef.current.forEach((chunk) => {
        const ratio =
          (recordingContextRef.current?.sampleRate || 16000) / sampleRate;
        for (let i = 0; i < chunk.length; i += ratio) {
          allSamples.push(chunk[Math.floor(i)] * 32767);
        }
      });
      const pcmData = new Int16Array(allSamples);
      onSendAudio(new Uint8Array(pcmData.buffer));
      audioChunksRef.current = [];
    }
  };

  // Use custom hook for WebSocket connection to reduce cognitive complexity
  const { socketRef, connectionStatus } = useWebSocketConnection(
    mode,
    sessionId,
    onLiveEvent,
    {
      onAudioData: (data) => {
        playbackQueueRef.current.push(data);
        aiTurnActiveRef.current = true;

        if (!isSpeakingRef.current) {
          isSpeakingRef.current = true;
          setIsSpeaking(true);
          isVoiceActiveRef.current = false;
          setIsVoiceActive(false);
          if (isRecordingRef.current) {
            isSendingAudioRef.current = false;
            teardownRecording(false);
          }
        }

        if (!isQueueProcessingRef.current) {
          processPlaybackQueue();
        }
      },
      onInterrupted: () => {
        console.log("[VOICE_FRONTEND] Interruption signal from relay");
        stopPlaybackImmediately();
        isVoiceActiveRef.current = false;
        setIsVoiceActive(false);
        if (playbackContextRef.current?.state === "running") {
          playbackContextRef.current.suspend().then(() => {
            nextStartTimeRef.current = 0;
            playbackContextRef.current?.resume();
          });
        }
        isSpeakingRef.current = false;
        aiTurnActiveRef.current = false;
        setIsSpeaking(false);
      },
      onTurnComplete: () => {
        aiTurnActiveRef.current = false;
        isSendingAudioRef.current = true;
        if (playbackQueueRef.current.length === 0) {
          isSpeakingRef.current = false;
          setIsSpeaking(false);
          queueResumeListening();
        }
      },
      onConnectionChange: (status) => {
        if (status === "closed") {
          stopPlaybackImmediately();
          teardownRecording(false);
        }
      },
    }
  );

  const processPlaybackQueue = async () => {
    if (playbackQueueRef.current.length === 0) return;

    // Use the shared ref-based AudioContext to avoid creating a new one per audio chunk
    let currentCtx = playbackContextRef.current;
    if (!currentCtx || currentCtx.state === "closed") {
      console.log(
        "[VOICE_DEBUG] Creating new playback AudioContext at 24000Hz",
      );
      currentCtx = new (
        globalThis.AudioContext || (globalThis as any).webkitAudioContext
      )({ sampleRate: 24000 });
      playbackContextRef.current = currentCtx;
      nextStartTimeRef.current = 0;
    }

    if (currentCtx.state === "suspended") {
      console.log("[VOICE_DEBUG] Resuming suspended playback AudioContext");
      try {
        await currentCtx.resume();
      } catch (e) {
        console.warn("Playback Context resume failed", e);
      }
    }

    // Double check state after resume attempt
    if (currentCtx.state !== "running") {
      console.warn(
        "[VOICE_DEBUG] Playback AudioContext is not running:",
        currentCtx.state,
      );
    }

    isQueueProcessingRef.current = true;

    // Crucial: Only set speaking to true if we're not already marked as speaking
    if (!isSpeakingRef.current) {
      isSpeakingRef.current = true;
      setIsSpeaking(true);
    }

    while (playbackQueueRef.current.length > 0) {
      const audioChunks = playbackQueueRef.current.shift();
      if (!audioChunks) break;
      const audioBuffer = currentCtx.createBuffer(1, audioChunks.length, 24000);
      audioBuffer.copyToChannel(audioChunks, 0);

      const source = currentCtx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(currentCtx.destination);
      activePlaybackSourcesRef.current.add(source);

      const now = currentCtx.currentTime;
      // Use a larger look-ahead buffer (0.1s) to prevent audio underrun/silence
      if (nextStartTimeRef.current < now) {
        nextStartTimeRef.current = now + 0.03;
      }

      source.start(nextStartTimeRef.current);
      nextStartTimeRef.current += audioBuffer.duration;

      source.onended = () => {
        activePlaybackSourcesRef.current.delete(source);
        // Only reset speaking status if no more audio chunks are queued AND AI is not currently generating more
        if (
          playbackQueueRef.current.length === 0 &&
          activePlaybackSourcesRef.current.size === 0
        ) {
          console.log("[VOICE_FRONTEND] Playback queue empty");
          // Important: We only mark speaking as false if turn is not active or we're waiting for user
          if (!aiTurnActiveRef.current) {
            isSpeakingRef.current = false;
            setIsSpeaking(false);
            queueResumeListening();
          }
        }
      };
    }

    isQueueProcessingRef.current = false;
  };

  const speakText = (text: string) => {
    if (!("speechSynthesis" in globalThis)) return;

    // Strip labels like "Question X of Y" or "Interview question" from the voice output
    const cleanText = text
      .replace(/^Question \d+ of \d+\n\n/i, "")
      .replace(/^Interview question\n\n/i, "")
      .replace(/^Interview complete\.\n\n/i, "");

    // Stop any current speech
    globalThis.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(cleanText);

    // Select a natural sounding voice if available
    const voices = globalThis.speechSynthesis.getVoices();
    const preferredVoice =
      voices.find(
        (v) => v.name.includes("Google") || v.name.includes("Natural"),
      ) || voices[0];
    if (preferredVoice) utterance.voice = preferredVoice;

    utterance.rate = 1;
    utterance.pitch = 1;

    utterance.onstart = () => {
      isSpeakingRef.current = true;
      setIsSpeaking(true);
    };
    utterance.onend = () => {
      isSpeakingRef.current = false;
      setIsSpeaking(false);
      if (mode === "VOICE" && !isRecordingRef.current) {
        // Delay slightly to avoid catching the end of the AI's own voice
        setTimeout(() => {
          if (!isSpeakingRef.current) startRecording();
        }, 500);
      }
    };

    globalThis.speechSynthesis.speak(utterance);
  };

  useEffect(() => {
    // Browser TTS fallback only if socket isn't active
    if (
      mode === "VOICE" &&
      history.length > 0 &&
      socketRef.current?.readyState !== WebSocket.OPEN
    ) {
      const lastMessage = history.at(-1);
      if (lastMessage?.role === "agent") {
        speakText(lastMessage.text);
      }
    }

    return () => {
      globalThis.speechSynthesis.cancel();
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
        silenceTimeoutRef.current = null;
      }
      if (resumeListeningTimeoutRef.current) {
        globalThis.clearTimeout(resumeListeningTimeoutRef.current);
        resumeListeningTimeoutRef.current = null;
      }
    };
  }, [history.length, mode]);

  const setupAudioContext = async (attemptId: number) => {
    let context = recordingContextRef.current;
    if (!context || context.state === "closed") {
      console.log("[VOICE_DEBUG] Creating new recording AudioContext");
      context = new (
        globalThis.AudioContext || (globalThis as any).webkitAudioContext
      )({ sampleRate: 16000 });
      recordingContextRef.current = context;
      context.onstatechange = () =>
        console.log("[VOICE_DEBUG] RecordingContext state:", context?.state);
      workletRegisteredRef.current = false;
    }

    if (context.state === "suspended") {
      console.log("[VOICE_DEBUG] Resuming recording AudioContext");
      await context.resume();
    }

    if (
      attemptId !== recordingAttemptRef.current ||
      isSpeakingRef.current ||
      aiTurnActiveRef.current ||
      socketRef.current?.readyState !== WebSocket.OPEN
    ) {
      console.log(
        "[VOICE_DEBUG] Aborting microphone start after context resume",
      );
      return null;
    }

    return context;
  };

  const registerAudioWorklet = async (context: AudioContext) => {
    if (workletRegisteredRef.current) return;

    const workletCode = `
      class AudioProcessor extends AudioWorkletProcessor {
        constructor() { 
          super();
          this.bufferSize = 1024;
          this.buffer = new ArrayBuffer(this.bufferSize * 2);
          this.view = new DataView(this.buffer);
          this.index = 0;
        }
        process(inputs) {
          const input = inputs[0][0];
          if (input) {
            for (let i = 0; i < input.length; i++) {
              let s = Math.max(-1, Math.min(1, input[i]));
              const pcm = s < 0 ? s * 0x8000 : s * 0x7FFF;
              this.view.setInt16(this.index * 2, pcm, true);
              this.index++;
              
              if (this.index >= this.bufferSize) {
                this.port.postMessage({ event: 'chunk', data: this.buffer.slice(0) });
                this.index = 0;
              }
            }
          }
          return true;
        }
      }
      registerProcessor('audio-recorder-worklet', AudioProcessor);
    `;

    const blob = new Blob([workletCode], {
      type: "application/javascript",
    });
    const url = URL.createObjectURL(blob);
    try {
      await context.audioWorklet.addModule(url);
      workletRegisteredRef.current = true;
    } finally {
      URL.revokeObjectURL(url);
    }
  };

  const startRecording = async () => {
    if (resumeListeningTimeoutRef.current) {
      globalThis.clearTimeout(resumeListeningTimeoutRef.current);
      resumeListeningTimeoutRef.current = null;
    }
    // Use refs for the guard to avoid stale closure issues
    if (
      isRecordingRef.current ||
      isSpeakingRef.current ||
      isStartingRecordingRef.current
    ) {
      console.log("[VOICE_DEBUG] startRecording blocked:", {
        isRecording: isRecordingRef.current,
        isSpeaking: isSpeakingRef.current,
        isStarting: isStartingRecordingRef.current,
      });
      return;
    }
    try {
      isStartingRecordingRef.current = true;
      const attemptId = ++recordingAttemptRef.current;
      hasDetectedSpeechRef.current = false;
      isVoiceActiveRef.current = false;
      isSendingAudioRef.current = mode === "VOICE" || mode === "CHAT";
      setIsVoiceActive(false);
      console.log("[VOICE_DEBUG] Requesting microphone access");
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      if (
        attemptId !== recordingAttemptRef.current ||
        isSpeakingRef.current ||
        aiTurnActiveRef.current ||
        socketRef.current?.readyState !== WebSocket.OPEN
      ) {
        console.log("[VOICE_DEBUG] Discarding stale microphone start");
        stream.getTracks().forEach((track) => track.stop());
        isStartingRecordingRef.current = false;
        return;
      }

      const track = stream.getAudioTracks()[0];
      const settings = track.getSettings();
      console.log("[VOICE_DEBUG] Mic Hardware Settings:", {
        sampleRate: settings.sampleRate,
        channelCount: settings.channelCount,
        deviceId: settings.deviceId,
      });

      // Use extracted functions to reduce complexity
      const context = await setupAudioContext(attemptId);
      if (!context) {
        stream.getTracks().forEach((track) => track.stop());
        isStartingRecordingRef.current = false;
        return;
      }

      await registerAudioWorklet(context);

      if (
        attemptId !== recordingAttemptRef.current ||
        isSpeakingRef.current ||
        aiTurnActiveRef.current ||
        socketRef.current?.readyState !== WebSocket.OPEN
      ) {
        console.log(
          "[VOICE_DEBUG] Aborting microphone start after worklet setup",
        );
        stream.getTracks().forEach((track) => track.stop());
        isStartingRecordingRef.current = false;
        return;
      }

      const source = context.createMediaStreamSource(stream);
      const workletNode = new AudioWorkletNode(
        context,
        "audio-recorder-worklet",
      );

      workletNode.port.onmessage = (ev) => {
        if (ev.data.event === "chunk") {
          if (
            mode === "VOICE" &&
            socketRef.current?.readyState === WebSocket.OPEN &&
            isSendingAudioRef.current
          ) {
            // Send raw binary to backend relay (same as example)
            socketRef.current.send(ev.data.data);
          } else if (mode === "CHAT") {
            // Only collect chunks for legacy buffer in CHAT mode
            audioChunksRef.current.push(new Float32Array(ev.data.data));
          }
        }
      };

      source.connect(workletNode);
      mediaStreamRef.current = stream;
      processorRef.current = workletNode;
      isRecordingRef.current = true;
      isStartingRecordingRef.current = false;
      isSendingAudioRef.current = mode === "VOICE" || mode === "CHAT";
      setIsRecording(true);

      // Organic VAD Logic
      if (mode === "VOICE") {
        const analyser = context.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);

        const bufferLength = analyser.fftSize;
        const dataArray = new Uint8Array(bufferLength);

        let lastSpeakTime = Date.now();
        let speechGateUntil = 0;
        let consecutiveSpeechFrames = 0;
        const recordingStartedAt = Date.now();
        // RMS-based VAD is more stable than frequency average for mic noise.
        const SPEECH_RMS_THRESHOLD = 0.035;
        const MIN_CONSECUTIVE_SPEECH_FRAMES = 4;
        const VAD_WARMUP_MS = 300;
        const MAX_RECORDING_TIME = 120000;

        silenceTimeoutRef.current = setTimeout(() => {
          console.log("VAD: Max recording time reached");
          stopRecording();
        }, MAX_RECORDING_TIME);

        const checkSilence = () => {
          if (!stream.active) return;
          if (socketRef.current?.readyState !== WebSocket.OPEN) {
            console.log(
              "[VOICE_FRONTEND] Stopping VAD because websocket is no longer open",
            );
            teardownRecording(false);
            return;
          }
          // If AI started speaking, we keep the mic open for "Organic" feel
          // but we can dampen it or ignore VAD events locally.
          // Gemini server-side VAD handles the turn taking.

          analyser.getByteTimeDomainData(dataArray);
          let sumSquares = 0;
          for (let i = 0; i < bufferLength; i++) {
            const normalized = (dataArray[i] - 128) / 128;
            sumSquares += normalized * normalized;
          }
          const rms = Math.sqrt(sumSquares / bufferLength);
          const speechDetectedNow =
            Date.now() - recordingStartedAt > VAD_WARMUP_MS &&
            rms > SPEECH_RMS_THRESHOLD;

          if (speechDetectedNow) {
            consecutiveSpeechFrames += 1;
          } else {
            consecutiveSpeechFrames = 0;
          }

          if (consecutiveSpeechFrames >= MIN_CONSECUTIVE_SPEECH_FRAMES) {
            lastSpeakTime = Date.now();
            speechGateUntil = lastSpeakTime + 250;
            if (!hasDetectedSpeechRef.current) {
              console.log("[VOICE] Speech detected", {
                rms: Number(rms.toFixed(4)),
              });
            }
            hasDetectedSpeechRef.current = true;
            isVoiceActiveRef.current = true;
            setIsVoiceActive(true);
            // ðŸ”¥ BARGE-IN (interrupt AI)
            if (isSpeakingRef.current) {
              console.log("[VOICE] Barge-in detected");
              stopPlaybackImmediately();
              // Native SDK handles interruption through incoming audio automatically.
            }
          } else if (isVoiceActiveRef.current && Date.now() > speechGateUntil) {
            isVoiceActiveRef.current = false;
            setIsVoiceActive(false);
          }

          animationFrameRef.current = requestAnimationFrame(checkSilence);
        };

        animationFrameRef.current = requestAnimationFrame(checkSilence);
      }
    } catch (error) {
      console.error("Error starting recording:", error);
      isStartingRecordingRef.current = false;
      isRecordingRef.current = false;
      setIsRecording(false);
    }
  };

  const stopRecording = (manual = false) => {
    teardownRecording(!manual);
  };

  const getStatusText = () => {
    if (isSpeaking) {
      return "Analyzing your profile...";
    }
    
    if (isRecording) {
      return "I'm listening to your response";
    }
    
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      return "Waiting for conversation...";
    }
    
    return "";
  };

  const getButtonIcon = () => {
    if (isRecording) {
      return (
        <svg
          className="w-10 h-10"
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
        </svg>
      );
    }
    
    if (isSpeaking) {
      return (
        <svg
          className="w-10 h-10"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"
          />
        </svg>
      );
    }
    
    return (
      <svg
        className="w-10 h-10"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
        />
      </svg>
    );
  };

  const getButtonClassName = () => {
    const baseClasses = "relative w-24 h-24 rounded-full flex items-center justify-center transition-all duration-500 shadow-xl";
    const disabledClasses = "disabled:opacity-50";
    
    let stateClasses;
    if (isRecording) {
      stateClasses = isVoiceActive
        ? "bg-red-500 text-white scale-110 shadow-red-200"
        : "bg-white border-2 border-red-200 text-red-500 shadow-red-100";
    } else if (isSpeaking) {
      stateClasses = "bg-blue-500 text-white shadow-blue-200";
    } else {
      stateClasses = "bg-white border-2 border-slate-100 text-slate-400 hover:border-slate-300 hover:text-slate-600";
    }
    
    return `${baseClasses} ${stateClasses} ${disabledClasses}`;
  };

  const getStatusIndicator = () => {
    if (isSpeaking) {
      return (
        <>
          <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
          AI Coach is Speaking
        </>
      );
    }
    
    if (isRecording) {
      return (
        <>
          <div
            className={`w-2 h-2 rounded-full ${isVoiceActive ? "bg-red-500 animate-pulse" : "bg-slate-300"}`}
          ></div>
          {isVoiceActive ? "Voice detected" : "Listening... (Your turn)"}
        </>
      );
    }
    
    if (isLoading) {
      return (
        <>
          <div className="w-2 h-2 rounded-full bg-slate-400 animate-spin"></div>
          Thinking...
        </>
      );
    }
    
    if (connectionStatus === "connected") {
      return (
        <span className="text-emerald-600 flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
          Coach is Ready
        </span>
      );
    }
    
    if (connectionStatus === "error" || connectionStatus === "closed") {
      return (
        <span className="text-red-500 flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></div>
          Connection Lost - Reconnecting...
        </span>
      );
    }
    
    return (
      <span className="text-amber-500 flex items-center gap-1.5">
        <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-bounce"></div>
        Initializing Voice Link...
      </span>
    );
  };

  const handleMicClick = async () => {
    // Crucial: AudioContext must be resumed from a user gesture
    try {
      if (
        !playbackContextRef.current ||
        playbackContextRef.current.state === "closed"
      ) {
        playbackContextRef.current = new (
          globalThis.AudioContext || (globalThis as any).webkitAudioContext
        )({ sampleRate: 24000 });
      }
      if (playbackContextRef.current.state === "suspended") {
        console.log(
          "[VOICE_FRONTEND] Resuming playback context from mic click",
        );
        await playbackContextRef.current.resume();
      }

      if (
        !recordingContextRef.current ||
        recordingContextRef.current.state === "closed"
      ) {
        recordingContextRef.current = new (
          globalThis.AudioContext || (globalThis as any).webkitAudioContext
        )({ sampleRate: 16000 });
      }
      if (recordingContextRef.current.state === "suspended") {
        console.log(
          "[VOICE_FRONTEND] Resuming recording context from mic click",
        );
        await recordingContextRef.current.resume();
      }
    } catch (e) {
      console.error("[VOICE_FRONTEND] Failed to resume contexts:", e);
    }

    if (mode !== "VOICE") return;

    // Manual fallback: If AI is stuck in speaking mode, allow force-stop/start
    if (isSpeakingRef.current || aiTurnActiveRef.current) {
      console.log(
        "[VOICE_FRONTEND] Manual Override: Forcing AI to stop and opening mic",
      );
      stopPlaybackImmediately();
      aiTurnActiveRef.current = false;
      startRecording();
      return;
    }

    if (isRecordingRef.current) {
      stopRecording(true);
    } else {
      startRecording();
    }
  };

  if (mode === "VOICE") {
    return (
      <div className="animate-in fade-in slide-in-from-bottom-2 duration-400 h-[calc(100vh-150px)] flex flex-col items-center justify-center space-y-12">
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
            {getStatusIndicator()}
          </div>
          <h3 className="text-xl font-medium text-slate-800 max-w-md mx-auto leading-relaxed h-8 text-center px-4">
            {getStatusText()}
          </h3>
        </div>

        <div className="relative">
          {/* Animated Waveform Background */}
          {((isVoiceActive && isRecording) || isSpeaking) && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div
                className={`absolute w-32 h-32 rounded-full opacity-20 animate-ping ${isSpeaking ? "bg-blue-400" : "bg-red-400"}`}
              ></div>
              <div
                className={`absolute w-40 h-40 rounded-full opacity-10 animate-pulse ${isSpeaking ? "bg-blue-400" : "bg-red-400"}`}
              ></div>
            </div>
          )}

          <button
            onClick={handleMicClick}
            disabled={isLoading}
            className={getButtonClassName()}
          >
            {getButtonIcon()}
          </button>
        </div>

        <div className="flex gap-6">
          <button
            onClick={onExit ?? (() => globalThis.location.reload())}
            className="text-[10px] font-bold text-slate-400 hover:text-slate-600 uppercase tracking-widest transition-colors"
          >
            Exit Interview
          </button>
          {connectionStatus !== "connected" && (
            <button
              onClick={() => globalThis.location.reload()}
              className="text-[10px] font-bold text-blue-500 hover:text-blue-700 uppercase tracking-widest transition-colors"
            >
              Reconnect
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-400 h-[calc(100vh-150px)] flex flex-col">
      <div className="flex-1 overflow-y-auto space-y-4 pr-3 mb-4 scrollbar-thin scrollbar-thumb-slate-200">
        {history.map((msg, i) => (
          <div
            key={`${msg.role}-${i}-${msg.text.slice(0, 20)}`}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[88%] p-3.5 rounded-xl text-[13px] leading-relaxed shadow-sm transition-all ${
                msg.role === "user"
                  ? "bg-slate-900 text-white rounded-tr-none"
                  : "bg-white text-slate-800 rounded-tl-none border border-slate-200"
              }`}
            >
              <div className="prose prose-sm max-w-none prose-slate">
                <ReactMarkdown
                  components={markdownComponents}
                >
                  {msg.text}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>

      {isComplete && (
        <div className="mb-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          Interview complete. Review your summary above and click Exit to leave
          the mock interview.
        </div>
      )}

      <form
        className="flex flex-col gap-3 pt-4 border-t border-slate-100"
        onSubmit={(e) => {
          e.preventDefault();
          if (isLoading || isComplete || !message.trim()) return;
          onSend(message.trim());
          setMessage("");
        }}
      >
        <textarea
          name="message"
          autoFocus
          autoComplete="off"
          rows={5}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (!isLoading && !isComplete && message.trim()) {
                onSend(message.trim());
                setMessage("");
              }
            }
          }}
          maxLength={4000}
          placeholder={
            isComplete
              ? "Interview is complete. Exit to return to the interview menu."
              : "Draft your response (Shift+Enter for newline, Enter to send)..."
          }
          disabled={isLoading || isComplete}
          className="flex-1 min-h-[140px] max-h-40 overflow-y-auto resize-y px-4 py-3 rounded-xl bg-white border border-slate-200 text-sm leading-relaxed focus:ring-1 focus:ring-slate-900 focus:outline-none transition-all placeholder:text-slate-400"
        />

        <div className="flex items-center justify-between gap-3">
          {onExit && (
            <button
              type="button"
              onClick={onExit}
              className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-all"
            >
              Exit Interview
            </button>
          )}

          <button
            type="submit"
            disabled={isLoading || isComplete}
            className="ml-auto bg-slate-900 text-white px-4 py-2 rounded-lg hover:bg-slate-800 disabled:opacity-50 flex items-center justify-center transition-all"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              ></path>
            </svg>
          </button>
        </div>
      </form>
    </div>
  );
};
