import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { AlignmentReport, ContentStrengthReport, ResumeSchema, ResumeCriticReport } from '../types';

export const UploadStep: React.FC<{ onUpload: (e: React.ChangeEvent<HTMLInputElement>) => void }> = ({ onUpload }) => (
  <div className="animate-in fade-in slide-in-from-bottom-2 duration-400">
    <div className="mb-8">
      <h3 className="text-xl font-semibold text-slate-900 mb-1.5">Resume Discovery</h3>
      <p className="text-[13px] text-slate-500 leading-relaxed">Let's extract your professional DNA. Upload your resume to start the optimization engine.</p>
    </div>
    
    <label className="flex flex-col items-center justify-center border border-slate-200 rounded-xl p-12 cursor-pointer hover:bg-slate-50/50 hover:border-slate-300 transition-all group relative overflow-hidden">
      <div className="w-12 h-12 bg-white border border-slate-100 rounded-lg flex items-center justify-center mb-4 shadow-sm group-hover:scale-105 transition-transform">
        <svg className="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
      </div>
      <span className="text-xs font-semibold text-slate-900 mb-1">Upload Resume</span>
      <span className="text-[11px] text-slate-400">PDF, TXT, or MD up to 10MB</span>
      <input type="file" className="hidden" onChange={onUpload} accept=".pdf,.txt,.md" />
    </label>
  </div>
);

export const CriticStep: React.FC<{ report: ResumeCriticReport; resume?: ResumeSchema | null; onApprove: () => void }> = ({ report, resume, onApprove }) => {
  const issues = Array.isArray(report.issues) ? report.issues : [];
  const score = typeof report.score === 'number' ? Math.round(report.score) : null;
  const summary = typeof report.summary === 'string' && report.summary.trim()
    ? report.summary
    : 'Resume processed successfully.';
  const severityClass = (severity: string) => {
    if (severity === 'HIGH') return 'bg-red-50 text-red-700 border-red-200';
    if (severity === 'MEDIUM') return 'bg-amber-50 text-amber-700 border-amber-200';
    return 'bg-slate-100 text-slate-600 border-slate-200';
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-400 space-y-6">
      <ReportHeader title="Resume Critique" summary={summary} score={score} />

      <div className="space-y-3">
        <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Issue List</h4>
        <div className="space-y-2">
          {issues.length === 0 && (
            <div className="p-3 bg-white border border-slate-200 rounded-lg text-xs text-slate-500">
              No critical issues detected. Proceed when ready.
            </div>
          )}
          {issues.map((issue, i) => (
            <div key={i} className="p-3 bg-white border border-slate-200 rounded-lg space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-900">{issue.type?.toUpperCase?.() || 'ISSUE'}</span>
                <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded border ${severityClass(issue.severity)}`}>
                  {issue.severity}
                </span>
              </div>
              <p className="text-[12px] text-slate-600 leading-relaxed">{issue.description}</p>
              {(() => {
                const resolved = resolveResumeLocation(resume, issue.location);
                return (
                  <div className="space-y-1.5 text-[10px] text-slate-400">
                    <div>
                      Section: <span className="font-medium text-slate-600">{capitalizeFirst(resolved.topLevel || 'unknown')}</span>
                    </div>
                    {resolved.isValid && (
                      <div className="text-slate-500">
                        Evidence: <span className="text-slate-700 line-clamp-5">
                          {resolved.usedSectionAsEvidence
                            ? capitalizeFirst(resolved.display || '')
                            : resolved.display}
                        </span>
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>
          ))}
        </div>
      </div>

      <button onClick={onApprove} className="w-full bg-slate-900 text-white text-[13px] font-semibold py-3 rounded-lg shadow-sm hover:bg-slate-800 active:scale-[0.98] transition-all">
        Run Content Strength Analysis
      </button>
    </div>
  );
};

export const ContentStep: React.FC<{ report: ContentStrengthReport; resume?: ResumeSchema | null; onApprove: () => void }> = ({ report, resume, onApprove }) => {
  const suggestions = Array.isArray(report.suggestions) ? report.suggestions : [];
  const score = typeof report.score === 'number' ? Math.round(report.score) : null;
  const summary = typeof report.summary === 'string' && report.summary.trim()
    ? report.summary
    : 'Content analysis complete.';
  const evidenceClass = (level: string) => {
    if (level === 'HIGH') return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    if (level === 'MEDIUM') return 'bg-amber-50 text-amber-700 border-amber-200';
    return 'bg-slate-100 text-slate-600 border-slate-200';
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-400 space-y-8">
      <ReportHeader title="Content Strength" summary={summary} score={score} />
      
      <div className="space-y-3">
         <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Revision Suggestions</h4>
         <div className="space-y-3">
           {suggestions.length === 0 && (
             <div className="p-3 bg-white border border-slate-200 rounded-lg text-xs text-slate-500">
               No suggestions returned. Proceed when ready.
             </div>
           )}
           {suggestions.map((sug, i) => (
             <div key={i} className="p-4 bg-white border border-slate-200 rounded-xl space-y-3">
               <div className="flex items-center justify-between">
                 <span className="text-[11px] font-semibold text-slate-900">{sug.type?.replace?.('_', ' ')?.toUpperCase?.() || 'SUGGESTION'}</span>
                 <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded border ${evidenceClass(sug.evidenceStrength)}`}>
                   {sug.evidenceStrength}
                 </span>
               </div>
               <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                 <div>
                   <p className="text-[9px] font-bold text-slate-500 uppercase mb-1">Original</p>
                   <p className="text-[11px] text-slate-500 line-through">{sug.original}</p>
                 </div>
                 <div>
                   <p className="text-[9px] font-bold text-emerald-600 uppercase mb-1">Suggested</p>
                   <p className="text-[11px] text-slate-900 font-medium">{sug.suggested}</p>
                 </div>
               </div>
               {(() => {
                 const resolved = resolveResumeLocation(resume, sug.location);
                 return (
                   <div className="space-y-1.5 text-[10px] text-slate-400">
                    <div>
                      Section: <span className="font-medium text-slate-600">{capitalizeFirst(resolved.topLevel || 'unknown')}</span>
                    </div>
                     {resolved.isValid && (
                       <div className="text-slate-500">
                         Evidence: <span className="text-slate-700">
                           {resolved.usedSectionAsEvidence
                             ? capitalizeFirst(resolved.display || '')
                             : resolved.display}
                         </span>
                       </div>
                     )}
                   </div>
                 );
               })()}
             </div>
           ))}
         </div>
      </div>

      <button onClick={onApprove} className="w-full bg-slate-900 text-white text-[13px] font-semibold py-3 rounded-lg shadow-sm hover:bg-slate-800 transition-all">
        Proceed to Job Alignment
      </button>
    </div>
  );
};

export const AlignmentStep: React.FC<{ 
  jd: string; 
  onChangeJD: (val: string) => void; 
  onAnalyze: () => void;
  isLoading: boolean;
}> = ({ jd, onChangeJD, onAnalyze, isLoading }) => {
  const MAX_JD_LENGTH = 20000;

  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-400 space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Role Fit Definition</h3>
        <span className={`text-[10px] font-medium ${jd.length > MAX_JD_LENGTH ? 'text-red-500' : 'text-slate-400'}`}>
          {jd.length.toLocaleString()} / {MAX_JD_LENGTH.toLocaleString()}
        </span>
      </div>
      <textarea
        className="w-full h-48 p-4 rounded-xl bg-white border border-slate-200 focus:ring-1 focus:ring-slate-900 focus:outline-none text-xs transition-all scrollbar-thin"
        placeholder="Paste the target job description here..."
        value={jd}
        maxLength={MAX_JD_LENGTH}
        onChange={(e) => onChangeJD(e.target.value)}
      />
      <button
        onClick={onAnalyze}
        disabled={!jd || isLoading}
        className="w-full bg-slate-900 disabled:opacity-50 text-white text-[13px] font-semibold py-3 rounded-lg shadow-sm hover:bg-slate-800 transition-all"
      >
        {isLoading ? 'Scanning Requirements...' : 'Analyze Market Fit'}
      </button>
    </div>
  );
};

export const AlignmentReportStep: React.FC<{ report: AlignmentReport; onStartInterview: () => void }> = ({ report, onStartInterview }) => (
  <div className="animate-in fade-in slide-in-from-bottom-2 duration-400 space-y-6">
    <div className="flex items-center justify-between border-b border-slate-100 pb-4">
      <h3 className="text-lg font-semibold">Match Report</h3>
      <span className="text-2xl font-bold text-slate-900">{report.fitScore}%</span>
    </div>
    
    <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
       <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Experience Match</p>
       <p className="text-xs text-slate-700 leading-relaxed font-medium italic">"{report.experienceMatch}"</p>
    </div>

    <div className="space-y-3">
      <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Reasoning</h4>
      <p className="text-[12px] text-slate-600 leading-relaxed">{report.reasoning}</p>
    </div>

    <div className="grid grid-cols-1 gap-3">
       <div className="p-3.5 bg-white border border-slate-200 rounded-xl">
          <p className="text-[9px] font-bold text-slate-400 uppercase mb-2 tracking-widest">Matched Skills</p>
          <div className="flex flex-wrap gap-1">
            {(report.skillsMatch || []).slice(0, 8).map((k, i) => (
              <span key={i} className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200 font-medium">{k}</span>
            ))}
          </div>
       </div>
       <div className="p-3.5 bg-white border border-slate-200 rounded-xl">
          <p className="text-[9px] font-bold text-slate-400 uppercase mb-2 tracking-widest">Missing Skills</p>
          <div className="flex flex-wrap gap-1">
            {(report.missingSkills || []).slice(0, 8).map((k, i) => (
              <span key={i} className="text-[10px] bg-red-50 text-red-600 px-2 py-0.5 rounded border border-red-100 font-medium">{k}</span>
            ))}
          </div>
       </div>
    </div>

    {/* Extract grounding sources and list them on the web app as per Google Search grounding rules */}
    {report.sources && report.sources.length > 0 && (
      <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl">
        <p className="text-[9px] font-bold text-slate-400 uppercase mb-2 tracking-widest">Market Context Sources</p>
        <div className="space-y-1.5">
          {report.sources.map((s, i) => (
            <a key={i} href={s.uri} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-[10px] text-blue-600 hover:text-blue-800 transition-colors font-medium truncate">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
              {s.title}
            </a>
          ))}
        </div>
      </div>
    )}
    
    <button onClick={onStartInterview} className="w-full bg-slate-900 text-white text-[13px] font-semibold py-3 rounded-lg shadow-sm hover:bg-slate-800 transition-all">
      Launch Mock Interview
    </button>
  </div>
);

export const InterviewModeSelectionStep: React.FC<{
  onSelect: (mode: InterviewMode) => void;
}> = ({ onSelect }) => (
  <div className="animate-in fade-in slide-in-from-bottom-2 duration-400 space-y-8">
    <div className="text-center">
      <h3 className="text-xl font-bold text-slate-900 mb-2">Select Interview Format</h3>
      <p className="text-sm text-slate-500">Choose how you'd like to practice today. This choice is final for this session.</p>
    </div>

    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <button 
        onClick={() => onSelect('CHAT')}
        className="flex flex-col items-center p-8 bg-white border border-slate-200 rounded-2xl hover:border-slate-900 hover:shadow-md transition-all group text-center"
      >
        <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-6 group-hover:bg-slate-900 group-hover:text-white transition-colors">
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        </div>
        <h4 className="font-bold text-lg mb-2">Text Chat</h4>
        <p className="text-xs text-slate-500 leading-relaxed">Standard text-based interface. Best for quick practice or public spaces.</p>
      </button>

      <button 
        onClick={() => onSelect('VOICE')}
        className="flex flex-col items-center p-8 bg-white border border-slate-200 rounded-2xl hover:border-slate-900 hover:shadow-md transition-all group text-center"
      >
        <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-6 group-hover:bg-slate-900 group-hover:text-white transition-colors">
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
        </div>
        <h4 className="font-bold text-lg mb-2">Organic Voice</h4>
        <p className="text-xs text-slate-500 leading-relaxed">Immersive voice simulation. Hands-free conversation with real-time audio analysis.</p>
      </button>
    </div>
  </div>
);

import { InterviewMessage, InterviewMode } from '../types';
import { resolveResumeLocation } from '@/utils/resolve-resume-location';
import { capitalizeFirst } from '@/utils/text';
import { ReportHeader } from './ReportHeader';

export const InterviewStep: React.FC<{ 
  history: InterviewMessage[]; 
  onSend: (msg: string) => void;
  onSendAudio: (audio: Uint8Array) => void;
  isLoading: boolean;
  chatEndRef: React.RefObject<HTMLDivElement>;
  mode: InterviewMode;
  sessionId: string;
  onExit?: () => void;
  onLiveEvent?: (event: { type: string; text?: string }) => void;
}> = ({ history, onSend, onSendAudio, isLoading, chatEndRef, mode, sessionId, onExit, onLiveEvent }) => {
  const [isRecording, setIsRecording] = React.useState(false);
  const [isSpeaking, setIsSpeaking] = React.useState(false);
  const [isVoiceActive, setIsVoiceActive] = React.useState(false);
  const [connectionStatus, setConnectionStatus] = React.useState<'connecting' | 'connected' | 'error' | 'closed'>('connecting');
  const audioChunksRef = React.useRef<Float32Array[]>([]);
  const playbackQueueRef = React.useRef<Float32Array[]>([]);
  const isQueueProcessingRef = React.useRef(false);
  const nextStartTimeRef = React.useRef(0);
  const animationFrameRef = React.useRef<number | null>(null);
  const silenceTimeoutRef = React.useRef<any | null>(null);
  const heartbeatIntervalRef = React.useRef<any | null>(null);
  const resumeListeningTimeoutRef = React.useRef<number | null>(null);
  const socketRef = React.useRef<WebSocket | null>(null);
  const liveSessionRef = React.useRef<any>(null);
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
  // Single shared AudioContext for playback — avoids creating a new one per audio chunk
  const playbackContextRef = React.useRef<AudioContext | null>(null);
  const activePlaybackSourcesRef = React.useRef<Set<AudioBufferSourceNode>>(new Set());
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
      window.clearTimeout(resumeListeningTimeoutRef.current);
      resumeListeningTimeoutRef.current = null;
    }

    resumeListeningTimeoutRef.current = window.setTimeout(() => {
      resumeListeningTimeoutRef.current = null;
      if (
        mode === 'VOICE' &&
        socketRef.current?.readyState === WebSocket.OPEN &&
        !isSpeakingRef.current &&
        !isRecordingRef.current &&
        !isStartingRecordingRef.current &&
        !aiTurnActiveRef.current
      ) {
        startRecording().catch((error) => {
          console.error('[VOICE_FRONTEND] Failed to resume listening:', error);
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
      currentStream.getTracks().forEach(track => track.stop());
    }

    if (shouldSignalAudioEnd && mode === 'VOICE' && socketRef.current?.readyState === WebSocket.OPEN) {
      console.log('[VOICE_FRONTEND] Signaling audio stream end to backend');
      socketRef.current.send(JSON.stringify({ type: 'realtimeInput', event: 'audio_stream_end' }));
    }

    if (mode === 'CHAT' && audioChunksRef.current.length > 0) {
      console.log('Processing legacy audio buffer for CHAT mode');
      const sampleRate = 16000;
      const allSamples: number[] = [];
      audioChunksRef.current.forEach(chunk => {
        const ratio = (recordingContextRef.current?.sampleRate || 16000) / sampleRate;
        for (let i = 0; i < chunk.length; i += ratio) {
          allSamples.push(chunk[Math.floor(i)] * 32767);
        }
      });
      const pcmData = new Int16Array(allSamples);
      onSendAudio(new Uint8Array(pcmData.buffer));
      audioChunksRef.current = [];
    }
  };

  // For Live Streaming Voice (Relay through Backend - Example SDK Pattern)
  useEffect(() => {
    if (mode !== 'VOICE') return;

    let isComponentMounted = true;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || window.location.origin;

    // Robustly construct the WebSocket URL to avoid double-slash issues.
    // If the base URL includes a protocol, strip it before prepending the ws protocol.
    const hostAndPath = API_BASE_URL.replace(/^https?:\/\//, '').replace(/\/$/, '');
    const wsUrl = `${protocol}//${hostAndPath}/api/v1/interview/live?sessionId=${sessionId}`;

    const initializeRelaySession = async () => {
      try {
        console.log('[VOICE_FRONTEND] Connecting to Backend Relay WebSocket...');
        const ws = new WebSocket(wsUrl);
        ws.binaryType = 'arraybuffer';
        socketRef.current = ws;

        ws.onopen = async () => {
          if (!isComponentMounted) return;
          console.log('[VOICE_FRONTEND] Relay Connection Established');
          setConnectionStatus('connected');

          // Start heartbeat to prevent infrastructure timeouts (Cloud Run/Nginx)
          if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ event: 'ping', type: 'control' }));
            }
          }, 25000); // 25s ping
          
          try {
            if (!playbackContextRef.current || playbackContextRef.current.state === 'closed') {
              playbackContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
            }
            await playbackContextRef.current.resume();
            
            if (!recordingContextRef.current || recordingContextRef.current.state === 'closed') {
              recordingContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
            }
            await recordingContextRef.current.resume();
            
            await startRecording();
          } catch (e) {
            console.error('[VOICE_FRONTEND] Setup failed:', e);
          }
        };

        ws.onmessage = (event) => {
          if (!isComponentMounted) return;

          if (event.data instanceof ArrayBuffer) {
            // Raw PCM audio from backend
            const binary = event.data;
            const dataView = new DataView(binary);
            const float32 = new Float32Array(binary.byteLength / 2);
            for (let i = 0; i < float32.length; i++) {
              float32[i] = dataView.getInt16(i * 2, true) / 32768;
            }

            playbackQueueRef.current.push(float32);
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
          } else if (typeof event.data === 'string') {
            try {
              const msg = JSON.parse(event.data);
              
              // Handle Interruption
              if (msg.type === 'interrupted') {
                console.log('[VOICE_FRONTEND] Interruption signal from relay');
                stopPlaybackImmediately();
                isVoiceActiveRef.current = false;
                setIsVoiceActive(false);
                if (playbackContextRef.current?.state === 'running') {
                  playbackContextRef.current.suspend().then(() => {
                    nextStartTimeRef.current = 0;
                    playbackContextRef.current?.resume();
                  });
                }
                isSpeakingRef.current = false;
                aiTurnActiveRef.current = false;
                setIsSpeaking(false);
              }

              // Handle Turn Completion
              if (msg.type === 'turn_complete') {
                aiTurnActiveRef.current = false;
                isSendingAudioRef.current = true;
                if (playbackQueueRef.current.length === 0) {
                  isSpeakingRef.current = false;
                  setIsSpeaking(false);
                  queueResumeListening();
                }
              }

              // Handle transcriptions (optional but good for UX)
              if (onLiveEvent) {
                onLiveEvent(msg);
              }
            } catch (e) {
              console.error('Relay message parse error:', e);
            }
          }
        };

        ws.onerror = (error) => {
          console.error('[VOICE_FRONTEND] Relay WebSocket Error:', error);
          setConnectionStatus('error');
        };

        ws.onclose = (event) => {
          console.log(`[VOICE_FRONTEND] Relay Connection Closed (Code: ${event.code}, Reason: ${event.reason || 'none'})`);
          setConnectionStatus('closed');
          if (heartbeatIntervalRef.current) {
            clearInterval(heartbeatIntervalRef.current);
            heartbeatIntervalRef.current = null;
          }
          stopPlaybackImmediately();
          teardownRecording(false);
        };
      } catch (err) {
        console.error('[VOICE_FRONTEND] Relay initialization failed:', err);
        setConnectionStatus('error');
      }
    };

    initializeRelaySession();

    return () => {
      isComponentMounted = false;
      stopPlaybackImmediately();
      teardownRecording(false);
      if (socketRef.current) {
        socketRef.current.close();
      }
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
      }
      if (resumeListeningTimeoutRef.current) {
        window.clearTimeout(resumeListeningTimeoutRef.current);
      }
    };
  }, [mode, sessionId]);

  const processPlaybackQueue = async () => {
    if (playbackQueueRef.current.length === 0) return;

    // Use the shared ref-based AudioContext to avoid creating a new one per audio chunk
    let currentCtx = playbackContextRef.current;
    if (!currentCtx || currentCtx.state === 'closed') {
      console.log('[VOICE_DEBUG] Creating new playback AudioContext at 24000Hz');
      currentCtx = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
      playbackContextRef.current = currentCtx;
      nextStartTimeRef.current = 0;
    }

    if (currentCtx.state === 'suspended') {
      console.log('[VOICE_DEBUG] Resuming suspended playback AudioContext');
      try { 
        await currentCtx.resume(); 
      } catch (e) { 
        console.warn('Playback Context resume failed', e); 
      }
    }

    // Double check state after resume attempt
    if (currentCtx.state !== 'running') {
      console.warn('[VOICE_DEBUG] Playback AudioContext is not running:', currentCtx.state);
    }

    isQueueProcessingRef.current = true;
    
    // Crucial: Only set speaking to true if we're not already marked as speaking
    if (!isSpeakingRef.current) {
        isSpeakingRef.current = true;
        setIsSpeaking(true);
    }

    while (playbackQueueRef.current.length > 0) {
      const audioChunks = playbackQueueRef.current.shift()!;
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
        if (playbackQueueRef.current.length === 0 && activePlaybackSourcesRef.current.size === 0) {
          console.log('[VOICE_FRONTEND] Playback queue empty');
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

  const playStreamedAudio = async (arrayBuffer: ArrayBuffer) => {
    // Legacy fallback for raw binary blobs
    try {
      let currentCtx = playbackContextRef.current;
      if (!currentCtx || currentCtx.state === 'closed') {
        currentCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
        playbackContextRef.current = currentCtx;
      }
      const audioBuffer = await currentCtx.decodeAudioData(arrayBuffer);
      const source = currentCtx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(currentCtx.destination);
      activePlaybackSourcesRef.current.add(source);
      source.onended = () => {
        activePlaybackSourcesRef.current.delete(source);
      };
      source.start();
    } catch (err) {
      console.error('Legacy playback failed:', err);
    }
  };

  const speakText = (text: string) => {
    if (!('speechSynthesis' in window)) return;
    
    // Strip labels like "Question X of Y" or "Interview question" from the voice output
    const cleanText = text
      .replace(/^Question \d+ of \d+\n\n/i, '')
      .replace(/^Interview question\n\n/i, '')
      .replace(/^Interview complete\.\n\n/i, '');

    // Stop any current speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(cleanText);
    
    // Select a natural sounding voice if available
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(v => v.name.includes('Google') || v.name.includes('Natural')) || voices[0];
    if (preferredVoice) utterance.voice = preferredVoice;
    
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    utterance.onstart = () => {
      isSpeakingRef.current = true;
      setIsSpeaking(true);
    };
    utterance.onend = () => {
          isSpeakingRef.current = false;
          setIsSpeaking(false);
          if (mode === 'VOICE' && !isRecordingRef.current) {
            // Delay slightly to avoid catching the end of the AI's own voice
            setTimeout(() => {
               if (!isSpeakingRef.current) startRecording();
            }, 500);
          }
        };

    window.speechSynthesis.speak(utterance);
  };

  useEffect(() => {
    // Browser TTS fallback only if socket isn't active
    if (mode === 'VOICE' && history.length > 0 && (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN)) {
      const lastMessage = history[history.length - 1];
      if (lastMessage.role === 'agent') {
        speakText(lastMessage.text);
      }
    }
    
    return () => {
      window.speechSynthesis.cancel();
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
        silenceTimeoutRef.current = null;
      }
      if (resumeListeningTimeoutRef.current) {
        window.clearTimeout(resumeListeningTimeoutRef.current);
        resumeListeningTimeoutRef.current = null;
      }
    };
  }, [history.length, mode]);

  const startRecording = async () => {
    if (resumeListeningTimeoutRef.current) {
      window.clearTimeout(resumeListeningTimeoutRef.current);
      resumeListeningTimeoutRef.current = null;
    }
    // Use refs for the guard to avoid stale closure issues
    if (isRecordingRef.current || isSpeakingRef.current || isStartingRecordingRef.current) {
      console.log('[VOICE_DEBUG] startRecording blocked:', {
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
      isSendingAudioRef.current = mode === 'VOICE' || mode === 'CHAT';
      setIsVoiceActive(false);
      console.log('[VOICE_DEBUG] Requesting microphone access');
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } 
      });

      if (
        attemptId !== recordingAttemptRef.current ||
        isSpeakingRef.current ||
        aiTurnActiveRef.current ||
        socketRef.current?.readyState !== WebSocket.OPEN
      ) {
        console.log('[VOICE_DEBUG] Discarding stale microphone start');
        stream.getTracks().forEach(track => track.stop());
        isStartingRecordingRef.current = false;
        return;
      }
      
      const track = stream.getAudioTracks()[0];
      const settings = track.getSettings();
      console.log('[VOICE_DEBUG] Mic Hardware Settings:', { 
        sampleRate: settings.sampleRate, 
        channelCount: settings.channelCount,
        deviceId: settings.deviceId
      });

      // Use a dedicated AudioContext for microphone capture (separate from playback)
      let context = recordingContextRef.current;
      if (!context || context.state === 'closed') {
        console.log('[VOICE_DEBUG] Creating new recording AudioContext');
        context = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
        recordingContextRef.current = context;
        context.onstatechange = () => console.log('[VOICE_DEBUG] RecordingContext state:', context?.state);
        workletRegisteredRef.current = false;
      }

      if (context.state === 'suspended') {
        console.log('[VOICE_DEBUG] Resuming recording AudioContext');
        await context.resume();
      }

      if (
        attemptId !== recordingAttemptRef.current ||
        isSpeakingRef.current ||
        aiTurnActiveRef.current ||
        socketRef.current?.readyState !== WebSocket.OPEN
      ) {
        console.log('[VOICE_DEBUG] Aborting microphone start after context resume');
        stream.getTracks().forEach(track => track.stop());
        isStartingRecordingRef.current = false;
        return;
      }

      if (!workletRegisteredRef.current) {
        const workletCode = `
          class AudioProcessor extends AudioWorkletProcessor {
            constructor() { 
              super();
              // Standard buffer size for 16kHz audio chunks
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
                  // Convert Float32 to Int16 Little-Endian for Gemini
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

        const blob = new Blob([workletCode], { type: 'application/javascript' });
        const url = URL.createObjectURL(blob);
        try {
          await context.audioWorklet.addModule(url);
          workletRegisteredRef.current = true;
        } finally {
          URL.revokeObjectURL(url);
        }
      }

      if (
        attemptId !== recordingAttemptRef.current ||
        isSpeakingRef.current ||
        aiTurnActiveRef.current ||
        socketRef.current?.readyState !== WebSocket.OPEN
      ) {
        console.log('[VOICE_DEBUG] Aborting microphone start after worklet setup');
        stream.getTracks().forEach(track => track.stop());
        isStartingRecordingRef.current = false;
        return;
      }
      
      const source = context.createMediaStreamSource(stream);
      const workletNode = new AudioWorkletNode(context, 'audio-recorder-worklet');
      
      workletNode.port.onmessage = (ev) => {
        if (ev.data.event === 'chunk') {
          if (mode === 'VOICE' && socketRef.current?.readyState === WebSocket.OPEN && isSendingAudioRef.current) {
            // Send raw binary to backend relay (same as example)
            socketRef.current.send(ev.data.data);
          } else if (mode === 'CHAT') {
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
      isSendingAudioRef.current = mode === 'VOICE' || mode === 'CHAT';
      setIsRecording(true);

      // Organic VAD Logic
      if (mode === 'VOICE') {
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
            console.log('[VOICE_FRONTEND] Stopping VAD because websocket is no longer open');
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

            // Renamed for clarity: this is the duration after which silence triggers a turn completion
            const USER_TURN_END_SILENCE_MS = 1200; 

            if (speechDetectedNow) {
                consecutiveSpeechFrames += 1;
            } else {
                consecutiveSpeechFrames = 0;
            }

            if (consecutiveSpeechFrames >= MIN_CONSECUTIVE_SPEECH_FRAMES) {
                lastSpeakTime = Date.now();
                speechGateUntil = lastSpeakTime + 250;
                if (!hasDetectedSpeechRef.current) {
                    console.log("[VOICE] Speech detected", { rms: Number(rms.toFixed(4)) });
                }
                hasDetectedSpeechRef.current = true;
                isVoiceActiveRef.current = true;
                setIsVoiceActive(true);
                // 🔥 BARGE-IN (interrupt AI)
                if (isSpeakingRef.current) {
                    console.log("[VOICE] Barge-in detected");
                    stopPlaybackImmediately();
                    // Native SDK handles interruption through incoming audio automatically.
                }

            } else {
                if (
                    isVoiceActiveRef.current &&
                    Date.now() > speechGateUntil
                ) {
                    isVoiceActiveRef.current = false;
                    setIsVoiceActive(false);
                }
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

  const handleMicClick = async () => {
    // Crucial: AudioContext must be resumed from a user gesture
    try {
      if (!playbackContextRef.current || playbackContextRef.current.state === 'closed') {
        playbackContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
      }
      if (playbackContextRef.current.state === 'suspended') {
        console.log('[VOICE_FRONTEND] Resuming playback context from mic click');
        await playbackContextRef.current.resume();
      }
      
      if (!recordingContextRef.current || recordingContextRef.current.state === 'closed') {
        recordingContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      }
      if (recordingContextRef.current.state === 'suspended') {
        console.log('[VOICE_FRONTEND] Resuming recording context from mic click');
        await recordingContextRef.current.resume();
      }
    } catch (e) {
      console.error('[VOICE_FRONTEND] Failed to resume contexts:', e);
    }

    if (mode !== 'VOICE') return;
    
    // Manual fallback: If AI is stuck in speaking mode, allow force-stop/start
    if (isSpeakingRef.current || aiTurnActiveRef.current) {
      console.log('[VOICE_FRONTEND] Manual Override: Forcing AI to stop and opening mic');
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

  if (mode === 'VOICE') {
    return (
      <div className="animate-in fade-in slide-in-from-bottom-2 duration-400 h-[calc(100vh-340px)] flex flex-col items-center justify-center space-y-12">
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
            {isSpeaking ? (
              <>
                <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
                AI Coach is Speaking
              </>
            ) : isRecording ? (
              <>
                <div className={`w-2 h-2 rounded-full ${isVoiceActive ? 'bg-red-500 animate-pulse' : 'bg-slate-300'}`}></div>
                {isVoiceActive ? 'Voice detected' : 'Listening... (Your turn)'}
              </>
            ) : isLoading ? (
              <>
                <div className="w-2 h-2 rounded-full bg-slate-400 animate-spin"></div>
                Thinking...
              </>
            ) : connectionStatus === 'connected' ? (
              <span className="text-emerald-600 flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
                Coach is Ready
              </span>
            ) : connectionStatus === 'error' || connectionStatus === 'closed' ? (
              <span className="text-red-500 flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></div>
                Connection Lost - Reconnecting...
              </span>
            ) : (
              <span className="text-amber-500 flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-bounce"></div>
                Initializing Voice Link...
              </span>
            )}
          </div>
          <h3 className="text-xl font-medium text-slate-800 max-w-md mx-auto leading-relaxed h-8 text-center px-4">
            {isSpeaking ? (
              "Analyzing your profile..."
            ) : isRecording ? (
              "I'm listening to your response"
            ) : socketRef.current?.readyState === WebSocket.OPEN ? (
              "Waiting for conversation..."
            ) : ""}
          </h3>
        </div>

        <div className="relative">
          {/* Animated Waveform Background */}
          {((isVoiceActive && isRecording) || isSpeaking) && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className={`absolute w-32 h-32 rounded-full opacity-20 animate-ping ${isSpeaking ? 'bg-blue-400' : 'bg-red-400'}`}></div>
              <div className={`absolute w-40 h-40 rounded-full opacity-10 animate-pulse ${isSpeaking ? 'bg-blue-400' : 'bg-red-400'}`}></div>
            </div>
          )}
          
          <button
            onClick={handleMicClick}
            disabled={isLoading}
            className={`relative w-24 h-24 rounded-full flex items-center justify-center transition-all duration-500 shadow-xl ${
              isRecording 
                ? isVoiceActive
                  ? 'bg-red-500 text-white scale-110 shadow-red-200'
                  : 'bg-white border-2 border-red-200 text-red-500 shadow-red-100'
                : isSpeaking 
                  ? 'bg-blue-500 text-white shadow-blue-200'
                  : 'bg-white border-2 border-slate-100 text-slate-400 hover:border-slate-300 hover:text-slate-600'
            } disabled:opacity-50`}
          >
            {isRecording ? (
              <svg className="w-10 h-10" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
              </svg>
            ) : isSpeaking ? (
              <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
              </svg>
            ) : (
              <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"></path>
              </svg>
            )}
          </button>
        </div>

        <div className="flex gap-6">
           <button 
             onClick={onExit ? onExit : () => window.location.reload()}
             className="text-[10px] font-bold text-slate-400 hover:text-slate-600 uppercase tracking-widest transition-colors"
           >
             Exit Interview
           </button>
           {connectionStatus !== 'connected' && (
             <button 
               onClick={() => window.location.reload()}
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
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-400 h-[calc(100vh-340px)] flex flex-col">
      <div className="flex-1 overflow-y-auto space-y-4 pr-3 mb-4 scrollbar-thin scrollbar-thumb-slate-200">
        {history.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[88%] p-3.5 rounded-xl text-[13px] leading-relaxed shadow-sm transition-all ${
              msg.role === 'user' ? 'bg-slate-900 text-white rounded-tr-none' : 'bg-white text-slate-800 rounded-tl-none border border-slate-200'
            }`}>
              <div className="prose prose-sm max-w-none prose-slate">
                <ReactMarkdown
                  components={{
                    p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                    ul: ({children}) => <ul className="list-disc pl-4 mb-2">{children}</ul>,
                    li: ({children}) => <li className="mb-0.5">{children}</li>,
                    strong: ({children}) => <span className="font-bold">{children}</span>,
                  }}
                >
                  {msg.text}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>

      <form
        className="flex gap-2 pt-4 border-t border-slate-100"
        onSubmit={(e) => {
          e.preventDefault();
          const input = (e.target as any).message;
          if (!input.value.trim() || isLoading) return;
          onSend(input.value);
          input.value = '';
        }}
      >
        <input
          name="message"
          autoFocus
          autoComplete="off"
          maxLength={4000}
          placeholder="Draft your response..."
          className="flex-1 px-4 py-2.5 rounded-lg bg-white border border-slate-200 text-xs focus:ring-1 focus:ring-slate-900 focus:outline-none transition-all placeholder:text-slate-400"
        />
        <button
          type="submit"
          disabled={isLoading}
          className="bg-slate-900 text-white px-4 rounded-lg hover:bg-slate-800 disabled:opacity-50 flex items-center justify-center transition-all"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg>
        </button>
      </form>
    </div>
  );
};
