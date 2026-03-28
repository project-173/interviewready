import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { StructuralAssessment, ContentAnalysisReport, AlignmentReport } from '../types';

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

export const CriticStep: React.FC<{ report: StructuralAssessment; onApprove: () => void }> = ({ report, onApprove }) => (
  <div className="animate-in fade-in slide-in-from-bottom-2 duration-400 space-y-6">
    <div className="flex items-center justify-between border-b border-slate-100 pb-4">
      <h3 className="text-lg font-semibold">Structural Audit</h3>
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Score</span>
        <span className="bg-slate-900 text-white text-sm font-bold px-2.5 py-1 rounded shadow-sm">{report.score}</span>
      </div>
    </div>
    
    <div className="p-5 bg-slate-50 border border-slate-200 rounded-xl">
      <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2.5">AI Summary</h4>
      <p className="text-[13px] text-slate-700 italic leading-relaxed">"{report.readability}"</p>
    </div>

    <div className="space-y-3">
      <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Formatting Recommendations</h4>
      <div className="space-y-2">
        {(report.formattingRecommendations || []).map((rec, i) => (
          <div key={i} className="flex items-start gap-3 p-3 bg-white border border-slate-200 rounded-lg text-xs text-slate-600 transition-colors hover:border-slate-300">
            <div className="mt-0.5 w-1.5 h-1.5 rounded-full bg-slate-400 flex-none"></div>
            {rec}
          </div>
        ))}
      </div>
    </div>

    {report.suggestions && report.suggestions.length > 0 && (
      <div className="space-y-3">
        <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Content Suggestions</h4>
        <div className="space-y-2">
          {(report.suggestions || []).map((suggestion, i) => (
            <div key={i} className="flex items-start gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-slate-600 transition-colors hover:border-blue-300">
              <div className="mt-0.5 w-1.5 h-1.5 rounded-full bg-blue-400 flex-none"></div>
              {suggestion}
            </div>
          ))}
        </div>
      </div>
    )}

    <button onClick={onApprove} className="w-full bg-slate-900 text-white text-[13px] font-semibold py-3 rounded-lg shadow-sm hover:bg-slate-800 active:scale-[0.98] transition-all">
      Run Content Strength Analysis
    </button>
  </div>
);

export const ContentStep: React.FC<{ report: ContentAnalysisReport; onApprove: () => void }> = ({ report, onApprove }) => (
  <div className="animate-in fade-in slide-in-from-bottom-2 duration-400 space-y-8">
    <div>
      <h3 className="text-lg font-semibold text-slate-900 mb-1">Content Analysis</h3>
      <p className="text-[12px] text-slate-500">{report.summary}</p>
    </div>
    
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="p-6 bg-white border border-slate-200 rounded-2xl flex flex-col items-center">
        <div className="relative w-24 h-24 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90">
              <circle cx="48" cy="48" r="40" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-slate-100" />
              <circle cx="48" cy="48" r="40" stroke="currentColor" strokeWidth="8" fill="transparent" 
                  strokeDasharray={251.2} 
                  strokeDashoffset={251.2 * (report.hallucinationRisk)} 
                  className="text-red-500 transition-all duration-1000" />
            </svg>
            <span className="absolute text-xl font-bold">{Math.round((1 - report.hallucinationRisk) * 100)}%</span>
        </div>
        <span className="mt-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Faithfulness Score</span>
      </div>

      <div className="p-6 bg-white border border-slate-200 rounded-2xl">
        <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">Key Achievements</h4>
         <div className="space-y-3">
          {(report.achievements || []).slice(0, 3).map((ach, i) => (
            <div key={i} className="text-[11px] text-slate-600 border-l-2 border-slate-200 pl-3">
              <p className="font-medium text-slate-900">{ach?.description}</p>
              <div className="flex gap-2 mt-1">
                <span className={`text-[9px] uppercase font-bold ${ach?.impact === 'HIGH' ? 'text-emerald-600' : 'text-amber-600'}`}>{ach?.impact} Impact</span>
                {ach?.quantifiable && <span className="text-[9px] uppercase font-bold text-blue-600">Quantified</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>

    <div className="space-y-3">
       <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Extracted Skills & Evidence</h4>
       <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
         {(report.skills || []).slice(0, 6).map((skill, i) => (
           <div key={i} className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
             <div className="flex justify-between items-start mb-1">
               <span className="text-[11px] font-bold text-slate-900">{skill?.name}</span>
               <span className="text-[9px] px-1.5 py-0.5 bg-white border border-slate-200 rounded text-slate-500">{skill?.category}</span>
             </div>
             <p className="text-[10px] text-slate-500 line-clamp-2 italic">"{skill?.evidence}"</p>
           </div>
         ))}
       </div>
    </div>

    <div className="space-y-3">
       <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Phrasing Suggestions</h4>
       <div className="space-y-2">
         {(report.suggestions || []).slice(0, 2).map((sug, i) => (
           <div key={i} className="p-4 bg-amber-50/30 border border-amber-100 rounded-xl">
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
               <div>
                 <p className="text-[9px] font-bold text-amber-600 uppercase mb-1">Original</p>
                 <p className="text-[11px] text-slate-500 line-through">{sug?.original}</p>
               </div>
               <div>
                 <p className="text-[9px] font-bold text-emerald-600 uppercase mb-1">Suggested</p>
                 <p className="text-[11px] text-slate-900 font-medium">{sug?.suggested}</p>
               </div>
             </div>
             <p className="mt-3 text-[10px] text-slate-600 bg-white/50 p-2 rounded border border-amber-100/50">{sug?.rationale}</p>
           </div>
         ))}
       </div>
    </div>

    <button onClick={onApprove} className="w-full bg-slate-900 text-white text-[13px] font-semibold py-3 rounded-lg shadow-sm hover:bg-slate-800 transition-all">
      Proceed to Job Alignment
    </button>
  </div>
);

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

export const InterviewStep: React.FC<{ 
  history: InterviewMessage[]; 
  onSend: (msg: string) => void;
  onSendAudio: (audio: Uint8Array) => void;
  isLoading: boolean;
  chatEndRef: React.RefObject<HTMLDivElement>;
  mode: InterviewMode;
  sessionId: string;
  onExit?: () => void;
}> = ({ history, onSend, onSendAudio, isLoading, chatEndRef, mode, sessionId, onExit }) => {
  const [isRecording, setIsRecording] = React.useState(false);
  const [isSpeaking, setIsSpeaking] = React.useState(false);
  const [connectionStatus, setConnectionStatus] = React.useState<'connecting' | 'connected' | 'error' | 'closed'>('connecting');
  const [mediaStream, setMediaStream] = React.useState<MediaStream | null>(null);
  const [processor, setProcessor] = React.useState<AudioWorkletNode | null>(null);
  const audioChunksRef = React.useRef<Float32Array[]>([]);
  const playbackQueueRef = React.useRef<Float32Array[]>([]);
  const isQueueProcessingRef = React.useRef(false);
  const nextStartTimeRef = React.useRef(0);
  const animationFrameRef = React.useRef<number | null>(null);
  const silenceTimeoutRef = React.useRef<any | null>(null);
  const socketRef = React.useRef<WebSocket | null>(null);
  const [liveTranscription, setLiveTranscription] = React.useState<string>("");

  // Refs to track current state inside stale closures (WebSocket handlers, timers, VAD)
  const isSpeakingRef = React.useRef(false);
  const isRecordingRef = React.useRef(false);
  // Single shared AudioContext for playback — avoids creating a new one per audio chunk
  const playbackContextRef = React.useRef<AudioContext | null>(null);
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

  // For Live Streaming Voice
  useEffect(() => {
    if (mode !== 'VOICE') return;

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || window.location.origin;
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    
    // Improved URL construction to handle various BASE_URL formats
    let cleanBaseUrl = API_BASE_URL.replace(/^https?:\/\//, '');
    if (cleanBaseUrl.endsWith('/')) {
      cleanBaseUrl = cleanBaseUrl.slice(0, -1);
    }
    
    const wsUrl = `${wsProtocol}//${cleanBaseUrl}/api/v1/interview/live?sessionId=${sessionId}`;
    console.log('Connecting to Voice WebSocket:', wsUrl);

    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = async () => {
      console.log('[VOICE_FRONTEND] Voice WebSocket connected');
      setConnectionStatus('connected');
      // Try to resume contexts — often fails without a user gesture, but worth a try
      try {
        if (playbackContextRef.current && playbackContextRef.current.state === 'suspended') {
          await playbackContextRef.current.resume();
        }
        if (recordingContextRef.current && recordingContextRef.current.state === 'suspended') {
          await recordingContextRef.current.resume();
        }
      } catch (e) {
        console.warn('[VOICE_FRONTEND] Eager context resume failed (expected if no gesture)', e);
      }
    };

    const base64ToFloat32 = (base64: string) => {
      const binary = atob(base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const int16 = new Int16Array(bytes.buffer);
      const float32 = new Float32Array(int16.length);
      for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 32768;
      return float32;
    };

    socket.onmessage = async (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.event === 'pong') {
          // Heartbeat received
          return;
        }
        
        console.log('[VOICE_FRONTEND] Received WebSocket message:', msg.type || msg.event || 'unknown');

        if (msg.type === 'audioStream') {
          const float32Data = base64ToFloat32(msg.data);
          playbackQueueRef.current.push(float32Data);
          
          // Mark as speaking as soon as we get audio chunks
          if (!isSpeakingRef.current) {
            console.log('[VOICE_FRONTEND] AI started speaking (audioStream)');
            isSpeakingRef.current = true;
            setIsSpeaking(true);
            if (isRecordingRef.current) {
              console.log('[VOICE_FRONTEND] Stopping recording due to AI speech');
              stopRecording();
            }
          }

          if (!isQueueProcessingRef.current) {
            processPlaybackQueue();
          }
        } else if (msg.type === 'textStream') {
          // Update history with live transcription if needed
          console.log('[VOICE_FRONTEND] AI Transcription:', msg.data);
          setLiveTranscription(msg.data);
          
          // Eagerly resume playback context if we receive text but context is suspended
          if (playbackContextRef.current && playbackContextRef.current.state === 'suspended') {
            playbackContextRef.current.resume().catch(console.error);
          }
        } else if (msg.type === 'inputTranscription') {
          console.log('[VOICE_FRONTEND] User Input Transcription:', msg.data);
          setLiveTranscription(msg.data);
        } else if (msg.interrupted) {
          // Clear playback queue if user interrupts AI
          console.log('[VOICE_FRONTEND] AI Interrupted, clearing playback queue');
          playbackQueueRef.current = [];
          isSpeakingRef.current = false;
          setIsSpeaking(false);
        } else if (msg.event === 'turn_complete' || msg.event === 'generation_complete') {
          // AI finished its turn — safe to open the microphone now
          console.log(`[VOICE_FRONTEND] AI Turn Finished: ${msg.event} — opening mic`);
          
          // Small delay to ensure last audio chunk is finished playing
          setTimeout(() => {
            if (!isRecordingRef.current && !isSpeakingRef.current) {
              console.log('[VOICE_FRONTEND] Automatically starting recording');
              startRecording();
            } else {
              console.log('[VOICE_FRONTEND] Automatic recording blocked:', { 
                isRecording: isRecordingRef.current, 
                isSpeaking: isSpeakingRef.current 
              });
            }
          }, 1000); // Increased delay slightly for safety
        } else if (msg.type === 'warning') {
          console.warn('AI Session Warning:', msg.data);
        } else if (msg.error) {
          console.error('WebSocket error message:', msg.error);
        }
      } catch (e) {
        // Fallback for raw binary if sent
        if (event.data instanceof Blob) {
          const arrayBuffer = await event.data.arrayBuffer();
          playStreamedAudio(arrayBuffer);
        }
      }
    };

    socket.onerror = (error) => {
      console.error('WebSocket Error:', error);
      setConnectionStatus('error');
      isSpeakingRef.current = false;
      isRecordingRef.current = false;
      setIsSpeaking(false);
      setIsRecording(false);
    };

    socket.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason || 'No reason provided');
      setConnectionStatus('closed');
      isSpeakingRef.current = false;
      isRecordingRef.current = false;
      setIsSpeaking(false);
      setIsRecording(false);
      
      // Cleanup contexts on close to prevent leaked resources/stuck states
      if (playbackContextRef.current) {
        playbackContextRef.current.close().catch(console.error);
        playbackContextRef.current = null;
      }
      if (recordingContextRef.current) {
        recordingContextRef.current.close().catch(console.error);
        recordingContextRef.current = null;
      }

      if (event.code !== 1000 && mode === 'VOICE') {
        alert(`Voice connection closed (Code ${event.code}). Please check your internet and API key.`);
      }
    };

    // Heartbeat to keep connection alive
    const heartbeat = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'realtimeInput', event: 'ping' }));
      }
    }, 5000);

    return () => {
      clearInterval(heartbeat);
      socket.close();
      if (playbackContextRef.current) {
        playbackContextRef.current.close().catch(console.error);
        playbackContextRef.current = null;
      }
      if (recordingContextRef.current) {
        recordingContextRef.current.close().catch(console.error);
        recordingContextRef.current = null;
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
    isSpeakingRef.current = true;
    setIsSpeaking(true);

    // Stop the microphone while the AI is speaking to prevent audio feedback
    if (isRecordingRef.current) {
      stopRecording();
    }

    while (playbackQueueRef.current.length > 0) {
      const audioChunks = playbackQueueRef.current.shift()!;
      const audioBuffer = currentCtx.createBuffer(1, audioChunks.length, 24000);
      audioBuffer.copyToChannel(audioChunks, 0);

      const source = currentCtx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(currentCtx.destination);

      const now = currentCtx.currentTime;
      // Use a larger look-ahead buffer (0.1s) to prevent audio underrun/silence
      if (nextStartTimeRef.current < now) {
        nextStartTimeRef.current = now + 0.1;
      }
      
      source.start(nextStartTimeRef.current);
      nextStartTimeRef.current += audioBuffer.duration;

      source.onended = () => {
        // Only reset speaking status if no more audio chunks are queued
        if (playbackQueueRef.current.length === 0) {
          console.log('[VOICE_FRONTEND] Playback queue empty, AI finished speaking');
          isSpeakingRef.current = false;
          setIsSpeaking(false);
        }
      };
      
      // Fallback: If onended never fires (can happen in some browsers if context is suspended)
      // we'll still reset state based on the calculated duration
      const timeoutMs = (audioBuffer.duration * 1000) + 100;
      setTimeout(() => {
        if (playbackQueueRef.current.length === 0 && isSpeakingRef.current) {
           console.log('[VOICE_FRONTEND] Playback fallback timeout reached');
           isSpeakingRef.current = false;
           setIsSpeaking(false);
        }
      }, timeoutMs);
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
    };
  }, [history.length, mode]);

  const startRecording = async () => {
    setLiveTranscription(""); // Reset for new turn
    // Use refs for the guard to avoid stale closure issues
    if (isRecordingRef.current || isSpeakingRef.current) {
      console.log('[VOICE_DEBUG] startRecording blocked:', { isRecording: isRecordingRef.current, isSpeaking: isSpeakingRef.current });
      return;
    }
    try {
      console.log('[VOICE_DEBUG] Requesting microphone access');
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } 
      });
      
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

      if (!workletRegisteredRef.current) {
        const workletCode = `
          class AudioProcessor extends AudioWorkletProcessor {
            constructor() { 
              super();
              // Increased buffer size to 4096 samples for network stability
              this.buffer = new Int16Array(4096);
              this.index = 0;
            }
            process(inputs) {
              const input = inputs[0][0];
              if (input) {
                for (let i = 0; i < input.length; i++) {
                  let s = Math.max(-1, Math.min(1, input[i]));
                  this.buffer[this.index++] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                  if (this.index >= this.buffer.length) {
                    this.port.postMessage({ event: 'chunk', data: this.buffer.slice().buffer });
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
      
      const source = context.createMediaStreamSource(stream);
      const workletNode = new AudioWorkletNode(context, 'audio-recorder-worklet');
      
      workletNode.port.onmessage = (ev) => {
        if (ev.data.event === 'chunk') {
          if (mode === 'VOICE' && socketRef.current?.readyState === WebSocket.OPEN) {
            const base64 = btoa(String.fromCharCode(...new Uint8Array(ev.data.data)));
            if (Math.random() < 0.05) console.log('[VOICE_DEBUG] Sending audio chunk to server');
            socketRef.current.send(JSON.stringify({ type: 'realtimeInput', audioData: base64 }));
          } else if (mode === 'CHAT') {
            // Only collect chunks for legacy buffer in CHAT mode
            audioChunksRef.current.push(new Float32Array(ev.data.data));
          }
        }
      };

      source.connect(workletNode);
      setMediaStream(stream);
      setProcessor(workletNode);
      isRecordingRef.current = true;
      setIsRecording(true);

      // Organic VAD Logic
      if (mode === 'VOICE') {
        const analyser = context.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);
        
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        
        let lastSpeakTime = Date.now();
        const SILENCE_THRESHOLD = 5;
        const SILENCE_DURATION = 4000;
        const MAX_RECORDING_TIME = 120000;

        silenceTimeoutRef.current = setTimeout(() => {
          console.log('VAD: Max recording time reached');
          stopRecording();
        }, MAX_RECORDING_TIME);

        const checkSilence = () => {
          if (!stream.active) return;
          
          // If AI started speaking, stop the mic immediately to prevent feedback
          if (isSpeakingRef.current) {
            console.log('[VOICE_DEBUG] VAD: AI is speaking, stopping mic to prevent feedback');
            stopRecording();
            return;
          }

          analyser.getByteFrequencyData(dataArray);
          const average = dataArray.reduce((x, y) => x + y) / bufferLength;

          if (average > SILENCE_THRESHOLD) {
            lastSpeakTime = Date.now();
          } else {
            // If silent for too long during a VOICE session, we could auto-stop
            // but for a live interview, we usually keep it open unless AI interrupts.
            const silentDuration = Date.now() - lastSpeakTime;
            if (silentDuration > SILENCE_DURATION) {
               // Aggressive silent logging for debugging
               if (Math.random() < 0.1) console.log('[VOICE_DEBUG] VAD: User silent for:', silentDuration);
            }
          }
          
          animationFrameRef.current = requestAnimationFrame(checkSilence);
        };
        
        animationFrameRef.current = requestAnimationFrame(checkSilence);
      }
    } catch (error) {
      console.error('Error starting recording:', error);
      isRecordingRef.current = false;
      setIsRecording(false);
    }
  };

  const stopRecording = (manual = false) => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }

    // Update the ref immediately so other closures see the change right away
    isRecordingRef.current = false;

    if (mediaStream && processor) {
      processor.disconnect();
      mediaStream.getTracks().forEach(track => track.stop());

      if (mode === 'CHAT' && audioChunksRef.current.length > 0) {
        // Handle legacy buffer only for CHAT mode audio capture
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
        audioChunksRef.current = []; // Clear for next time
      }

      setMediaStream(null);
      setProcessor(null);
      setIsRecording(false);
    }
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
    if (isSpeakingRef.current) {
      console.log('[VOICE_FRONTEND] Manual Override: Forcing AI to stop and opening mic');
      playbackQueueRef.current = [];
      isSpeakingRef.current = false;
      setIsSpeaking(false);
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
                <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></div>
                Listening... (Your turn)
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
            {liveTranscription ? (
              <span className="italic text-slate-600 animate-in fade-in duration-300">
                "{liveTranscription}"
              </span>
            ) : isSpeaking ? (
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
          {(isRecording || isSpeaking) && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className={`absolute w-32 h-32 rounded-full opacity-20 animate-ping ${isSpeaking ? 'bg-blue-400' : 'bg-red-400'}`}></div>
              <div className={`absolute w-40 h-40 rounded-full opacity-10 animate-pulse ${isSpeaking ? 'bg-blue-400' : 'bg-red-400'}`}></div>
            </div>
          )}
          
          <button
            onClick={handleMicClick}
            disabled={isLoading || isSpeaking}
            className={`relative w-24 h-24 rounded-full flex items-center justify-center transition-all duration-500 shadow-xl ${
              isRecording 
                ? 'bg-red-500 text-white scale-110 shadow-red-200' 
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

        <div className="flex gap-4">
           <button 
             onClick={onExit ? onExit : () => window.location.reload()}
             className="text-[10px] font-bold text-slate-400 hover:text-slate-600 uppercase tracking-widest transition-colors"
           >
             Exit Interview
           </button>
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