
import React from 'react';
import ReactMarkdown from 'react-markdown';
import { ResumeCriticReport, ContentStrengthReport, AlignmentReport, ResumeSchema } from '../types';
import { capitalizeFirst } from '../utils/text';
import { resolveResumeLocation } from '@/utils/resolve-resume-location';

const ReportHeader: React.FC<{
  title: string;
  summary: string;
  score?: number | string | null;
  scoreLabel?: string;
}> = ({ title, summary, score, scoreLabel = 'Score' }) => {
  const hasScore = score !== null && score !== undefined && score !== '';
  return (
    <div className="flex items-start justify-between border-b border-slate-100 pb-4 gap-4">
      <div className="min-w-0">
        <h3 className="text-lg font-semibold text-slate-900 mb-1">{title}</h3>
        <p className="text-[12px] text-slate-500 leading-relaxed line-clamp-3">"{summary}"</p>
      </div>
      {hasScore && (
        <div className="text-right flex-none">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{scoreLabel}</div>
          <div className="text-2xl font-bold text-slate-900">{score}</div>
        </div>
      )}
    </div>
  );
};

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
  const issues = Array.isArray(report.issueList) ? report.issueList : [];
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
                    {resolved.isValid ? (
                      <div className="text-slate-500">
                        Evidence: <span className="text-slate-700">
                          {resolved.usedSectionAsEvidence
                            ? capitalizeFirst(resolved.display || '')
                            : resolved.display}
                        </span>
                      </div>
                    ) : (
                      <div className="text-amber-600">Evidence not found in resume.</div>
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
                     {resolved.isValid ? (
                       <div className="text-slate-500">
                         Evidence: <span className="text-slate-700">
                           {resolved.usedSectionAsEvidence
                             ? capitalizeFirst(resolved.display || '')
                             : resolved.display}
                         </span>
                       </div>
                     ) : (
                       <div className="text-amber-600">Evidence not found in resume.</div>
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
    <ReportHeader
      title="Match Report"
      summary={report.experienceMatch}
      score={`${report.fitScore}%`}
      scoreLabel="Score"
    />

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

export const InterviewStep: React.FC<{ 
  history: { role: 'user' | 'agent'; text: string }[]; 
  onSend: (msg: string) => void;
  onSendAudio: (audio: Uint8Array) => void;
  isLoading: boolean;
  chatEndRef: React.RefObject<HTMLDivElement>;
}> = ({ history, onSend, onSendAudio, isLoading, chatEndRef }) => {
  const [isRecording, setIsRecording] = React.useState(false);
  const [mediaRecorder, setMediaRecorder] = React.useState<MediaRecorder | null>(null);
  const [audioChunks, setAudioChunks] = React.useState<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      recorder.onstop = () => {
        const audioBlob = new Blob(chunks, { type: 'audio/wav' });
        audioBlob.arrayBuffer().then(buffer => {
          onSendAudio(new Uint8Array(buffer));
        });
        stream.getTracks().forEach(track => track.stop());
      };

      setMediaRecorder(recorder);
      setAudioChunks(chunks);
      recorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Error starting recording:', error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  const handleMicClick = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

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
          type="button"
          onClick={handleMicClick}
          disabled={isLoading}
          className={`px-4 py-2.5 rounded-lg border transition-all flex items-center justify-center ${
            isRecording 
              ? 'bg-red-500 border-red-500 text-white animate-pulse' 
              : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
          } disabled:opacity-50`}
        >
          <svg className="w-4 h-4" fill={isRecording ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"></path>
          </svg>
        </button>
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
