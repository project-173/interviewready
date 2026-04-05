import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  SharedState, 
  WorkflowStatus,
  ChatRequest,
  InterviewMode,
  InterviewMessage,
  Resume
} from './types';

const DEFAULT_RESUME: Resume = {
  work: [],
  education: [],
  awards: [],
  certificates: [],
  skills: [],
  projects: []
};
import {
  contentStrengthAgent, 
  alignmentAgent,
  backendService 
} from './backendService';
import { StepIndicator } from './components/StepIndicator';
import { ResumePreview } from './components/ResumePreview';
import { LoadingState } from './components/LoadingState';
import { LoadingProvider, useLoading } from './contexts/LoadingContext';
import { 
  UploadStep, 
  CriticStep, 
  ContentStep, 
  AlignmentStep, 
  AlignmentReportStep, 
  InterviewStep,
  InterviewModeSelectionStep
} from './components/WorkflowSteps';

const isInterviewCompleteResponse = (text: string) =>
  text.toLowerCase().includes('interview complete');

const AppContent: React.FC = () => {
  const [state, setState] = useState<SharedState>(() => {
    const saved = localStorage.getItem('interview_ready_state');
    if (saved) return JSON.parse(saved);
    return {
      currentResume: DEFAULT_RESUME,
      history: [],
      jobDescription: '',
      status: WorkflowStatus.IDLE,
      criticReport: null,
      contentReport: null,
      alignmentReport: null,
      interviewHistory: [],
      extractionReview: null
    };
  });

  const [error, setError] = useState<string | null>(null);
  const [sessionReady, setSessionReady] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const initSession = async () => {
      try {
        await backendService.initialize();
        setSessionReady(true);
      } catch (err) {
        setError(`Failed to initialize session: ${err}`);
      }
    };
    initSession();
  }, []);

  useEffect(() => {
    localStorage.setItem('interview_ready_state', JSON.stringify(state));
  }, [state]);

  const resetSession = useCallback(() => {
    if (confirm('Reset current progress? This will clear all data and start over.')) {
      localStorage.removeItem('interview_ready_state');
      setState({
        currentResume: DEFAULT_RESUME,
        history: [],
        jobDescription: '',
        status: WorkflowStatus.IDLE,
        criticReport: null,
        contentReport: null,
        alignmentReport: null,
        interviewHistory: [],
        extractionReview: null
      });
      setError(null);
    }
  }, []);

  const handleStepClick = useCallback((status: WorkflowStatus) => {
    const canNavigate: Partial<Record<WorkflowStatus, boolean>> = {
      [WorkflowStatus.IDLE]: true,
      [WorkflowStatus.CRITIQUING]: !!state.currentResume,
      [WorkflowStatus.ANALYZING_CONTENT]: !!state.criticReport,
      [WorkflowStatus.ALIGNING_JD]: !!state.contentReport,
      [WorkflowStatus.INTERVIEWING]: !!state.alignmentReport,
    };

    if (!canNavigate[status]) return;

    const completedStatus: Partial<Record<WorkflowStatus, WorkflowStatus>> = {
      [WorkflowStatus.CRITIQUING]: WorkflowStatus.AWAITING_CRITIC_APPROVAL,
      [WorkflowStatus.ANALYZING_CONTENT]: WorkflowStatus.AWAITING_CONTENT_APPROVAL,
      [WorkflowStatus.ALIGNING_JD]: WorkflowStatus.AWAITING_ALIGNMENT_APPROVAL,
    };

    const reportAvailable: Partial<Record<WorkflowStatus, boolean>> = {
      [WorkflowStatus.CRITIQUING]: !!state.criticReport,
      [WorkflowStatus.ANALYZING_CONTENT]: !!state.contentReport,
      [WorkflowStatus.ALIGNING_JD]: !!state.alignmentReport,
    };

    const targetStatus =
      (reportAvailable[status] && completedStatus[status]) || status;

    setState(prev => ({ ...prev, status: targetStatus }));
  }, [state.currentResume, state.criticReport, state.contentReport, state.alignmentReport]);

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-white text-slate-950">
      {/* 1. Primary SaaS Navbar */}
      <nav className="h-16 flex-none bg-white border-b border-slate-200 px-6 flex items-center justify-between z-40">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-slate-900 rounded-lg flex items-center justify-center text-white font-bold text-lg">IR</div>
          <div>
            <span className="font-bold text-sm">InterviewReady</span>
            <span className="ml-2 px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 text-[10px] font-medium uppercase tracking-wider">Beta</span>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <button 
            onClick={resetSession}
            className="text-xs font-medium text-slate-500 hover:text-slate-900 transition-colors"
          >
            Reset Session
          </button>
          <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-[10px] font-bold text-slate-500 border border-slate-300">
            JD
          </div>
        </div>
      </nav>

      {/* 2. Secondary Workflow Indicator Bar - Centered width */}
      <div className="h-14 flex-none bg-slate-50/50 border-b border-slate-200 flex items-center px-6 z-30">
        <div className="w-full max-w-4xl mx-auto flex justify-center overflow-x-auto no-scrollbar">
          <StepIndicator currentStatus={state.status} onStepClick={handleStepClick} />
        </div>
      </div>

      {/* 3. Main Split Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel: Analysis & Actions */}
        <aside className="w-[450px] border-r border-slate-200 bg-white flex flex-col z-20 overflow-hidden">
          <div className="flex-1 overflow-y-auto p-8 space-y-8 scrollbar-thin scrollbar-thumb-slate-200">
            {error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start justify-between gap-3 text-red-700 animate-in fade-in slide-in-from-top-1">
                <div className="flex items-start gap-3 flex-1">
                  <div className="mt-0.5 text-red-500">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" /></svg>
                  </div>
                  <div className="text-xs font-medium">{error}</div>
                </div>
                <button
                  type="button"
                  onClick={() => setError(null)}
                  aria-label="Close notification"
                  className="text-red-500 hover:text-red-700 focus:outline-none focus:ring-2 focus:ring-red-200 rounded-full"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
              </div>
            )}

            {!sessionReady ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900"></div>
              </div>
            ) : (
              <div className="relative">
                <WorkflowController 
                  state={state} 
                  setState={setState} 
                  setError={setError}
                  chatEndRef={chatEndRef}
                />
              </div>
            )}
          </div>

          <div className="p-4 border-t border-slate-200 bg-slate-50/50 flex items-center justify-between text-[10px] text-slate-400 font-medium uppercase tracking-tight">
             <span>System Status: Operational</span>
             <span className="flex items-center gap-1.5">
               <div className="w-1.5 h-1.5 rounded-full bg-green-500"></div>
               Cloud Sync Active
             </span>
          </div>
        </aside>

        {/* Right Panel: Resume Preview */}
        <main className="flex-1 bg-slate-100/30 overflow-hidden flex flex-col relative">
          <div className="flex-1 overflow-y-auto">
            <ResumePreview resume={state.currentResume} />
          </div>
        </main>
      </div>

      {/* Centralized Loading Overlay */}
      <LoadingStateWrapper />
    </div>
  );
};

// Separate component to handle loading context
const WorkflowController: React.FC<{
  state: SharedState;
  setState: React.Dispatch<React.SetStateAction<SharedState>>;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
  chatEndRef: React.RefObject<HTMLDivElement>;
}> = ({ state, setState, setError, chatEndRef }) => {
  const { startLoading, updateProgress, stopLoading } = useLoading();
  const [manualResumeText, setManualResumeText] = useState('');
  const [manualResumeError, setManualResumeError] = useState<string | null>(null);

  const MAX_FILE_SIZE = 10 * 1024 * 1024;

  const isRecord = (value: unknown): value is Record<string, any> =>
    typeof value === 'object' && value !== null && !Array.isArray(value);

  const getResponseMetadata = (response: any) => {
    const payloadMetadata =
      isRecord(response?.payload) && isRecord((response.payload as any).metadata)
        ? (response.payload as any).metadata
        : null;
    const directMetadata = isRecord(response?.metadata) ? response.metadata : null;
    return directMetadata ?? payloadMetadata;
  };

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (file.size > MAX_FILE_SIZE) {
        reject(new Error(`File size exceeds ${MAX_FILE_SIZE / (1024 * 1024)}MB limit`));
        return;
      }
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve((reader.result as string).split(',')[1]);
      reader.onerror = reject;
    });
  };

const handleUploadSubmit = async (file: File | null) => {
  setError(null);
  setManualResumeError(null);

  // CASE 1: File provided → extract → critic
  if (file) {
    startLoading('Analyzing your resume...', [
      'Uploading file',
      'Extracting content',
      'Analyzing structure',
      'Generating insights'
    ]);

    try {
      if (file.type === 'application/pdf') {
        updateProgress(25, 0);

        const base64 = await fileToBase64(file);

        updateProgress(50, 1);

        const request: ChatRequest = {
          intent: 'RESUME_CRITIC',
          resumeData: null,
          jobDescription: '',
          messageHistory: [],
          resumeFile: { data: base64, fileType: 'pdf' }
        };

        updateProgress(75, 2);

        const response = await backendService.callChatEndpoint(request);
        const parsedResume = await backendService.fetchCurrentResume();

        let responseData;
        try {
          responseData = response.payload || JSON.parse(response.content || '{}');
        } catch {
          throw new Error('Invalid response from backend');
        }

        const metadata = getResponseMetadata(response);
        const needsReview = Boolean(metadata?.review_required ?? metadata?.needs_review);
        const reviewPayload =
          metadata?.review_payload ||
          (isRecord(response.payload) ? (response.payload as any).review_payload : null);
        const checkpointId = metadata?.checkpoint_id;

        updateProgress(90, 3);

        if (needsReview) {
          if (reviewPayload?.extracted_data) {
            setManualResumeText(JSON.stringify(reviewPayload.extracted_data, null, 2));
          }
          setState(prev => ({
            ...prev,
            currentResume: parsedResume || prev.currentResume,
            history: parsedResume ? [...prev.history, parsedResume] : prev.history,
            criticReport: null,
            status: WorkflowStatus.IDLE,
            extractionReview: {
              needsReview: true,
              checkpointId,
              reviewPayload,
            }
          }));

          updateProgress(100, 3);
          return;
        }

        setState(prev => ({
          ...prev,
          currentResume: parsedResume || prev.currentResume,
          history: parsedResume ? [...prev.history, parsedResume] : prev.history,
          criticReport: responseData,
          status: WorkflowStatus.AWAITING_CRITIC_APPROVAL,
          extractionReview: null,
        }));
        setManualResumeText('');

        updateProgress(100, 3);
      }
    } catch (err: any) {
      setError(err.message || "Failed to process resume");
    } finally {
      stopLoading();
    }

    return;
  }

  // CASE 2: No file → use resume from preview panel
  if (!state.currentResume) {
    setError('No resume available. Please upload or edit your resume.');
    return;
  }

  startLoading('Analyzing your resume...', [
    'Validating resume',
    'Analyzing structure',
    'Generating insights'
  ]);

  try {
    updateProgress(50, 1);

    const report = await backendService.resumeCriticAgent(state.currentResume);

    updateProgress(100, 2);

    setState(prev => ({
      ...prev,
      criticReport: report,
      status: WorkflowStatus.AWAITING_CRITIC_APPROVAL,
      extractionReview: null,
    }));
  } catch (err: any) {
    setError(err.message || 'Failed to analyze resume');
  } finally {
    stopLoading();
  }
};

  const submitManualResume = async () => {
    setManualResumeError(null);
    let parsed: any;
    try {
      parsed = JSON.parse(manualResumeText);
    } catch (error) {
      setManualResumeError('Manual resume data must be valid JSON.');
      return;
    }

    if (!parsed || typeof parsed !== 'object') {
      setManualResumeError('Manual resume data must be a JSON object.');
      return;
    }

    startLoading('Analyzing your resume...', ['Validating manual input', 'Analyzing structure', 'Generating insights']);
    try {
      updateProgress(35, 0);
      const report = await backendService.resumeCriticAgent(parsed);
      updateProgress(100, 2);
      setState(prev => ({
        ...prev,
        currentResume: parsed,
        history: [...prev.history, parsed],
        criticReport: report,
        status: WorkflowStatus.AWAITING_CRITIC_APPROVAL,
        extractionReview: null,
      }));
      setManualResumeText('');
    } catch (err: any) {
      setManualResumeError(err.message || 'Failed to process manual resume data.');
    } finally {
      stopLoading();
    }
  };

  const submitReviewResume = async () => {
    setManualResumeError(null);
    const checkpointId = state.extractionReview?.checkpointId;
    if (!checkpointId) {
      setManualResumeError('Missing checkpoint id for review resume.');
      return;
    }

    let parsed: any;
    try {
      parsed = JSON.parse(manualResumeText);
    } catch (error) {
      setManualResumeError('Review edits must be valid JSON.');
      return;
    }

    if (!parsed || typeof parsed !== 'object') {
      setManualResumeError('Review edits must be a JSON object.');
      return;
    }

    startLoading('Applying your edits...', ['Validating updates', 'Re-running review', 'Continuing analysis']);
    try {
      updateProgress(35, 0);
      const request: ChatRequest = {
        intent: 'RESUME_CRITIC',
        control: 'resume',
        checkpointId,
        resumeData: parsed,
        jobDescription: '',
        messageHistory: []
      };

      const response = await backendService.callChatEndpoint(request);
      const parsedResume = await backendService.fetchCurrentResume();
      const metadata = getResponseMetadata(response);
      const needsReview = Boolean(metadata?.review_required ?? metadata?.needs_review);
      const reviewPayload =
        metadata?.review_payload ||
        (isRecord(response.payload) ? (response.payload as any).review_payload : null);
      const nextCheckpointId = metadata?.checkpoint_id || checkpointId;

      updateProgress(70, 1);

      if (needsReview) {
        if (reviewPayload?.extracted_data) {
          setManualResumeText(JSON.stringify(reviewPayload.extracted_data, null, 2));
        }
        setState(prev => ({
          ...prev,
          currentResume: parsedResume || prev.currentResume,
          history: parsedResume ? [...prev.history, parsedResume] : prev.history,
          criticReport: null,
          status: WorkflowStatus.IDLE,
          extractionReview: {
            needsReview: true,
            checkpointId: nextCheckpointId,
            reviewPayload,
          }
        }));
        updateProgress(100, 2);
        return;
      }

      let responseData;
      try {
        responseData = response.payload || JSON.parse(response.content || '{}');
      } catch {
        throw new Error('Invalid response from backend');
      }

      updateProgress(100, 2);
      setState(prev => ({
        ...prev,
        currentResume: parsedResume || prev.currentResume,
        history: parsedResume ? [...prev.history, parsedResume] : prev.history,
        criticReport: responseData,
        status: WorkflowStatus.AWAITING_CRITIC_APPROVAL,
        extractionReview: null,
      }));
      setManualResumeText('');
    } catch (err: any) {
      setManualResumeError(err.message || 'Failed to process review edits.');
    } finally {
      stopLoading();
    }
  };

  const approveCritic = async () => {
    setState(prev => ({ ...prev, status: WorkflowStatus.ANALYZING_CONTENT }));
    startLoading('Analyzing content strength...', ['Extracting skills', 'Analyzing achievements', 'Generating suggestions']);
    try {
      updateProgress(50, 1);
      const report = await contentStrengthAgent(state.currentResume);
      updateProgress(100, 2);
      setState(prev => ({ ...prev, contentReport: report, status: WorkflowStatus.AWAITING_CONTENT_APPROVAL }));
    } catch (err: any) {
      setError(err.message);
    } finally {
      stopLoading();
    }
  };

  const approveContent = () => setState(prev => ({ ...prev, status: WorkflowStatus.ALIGNING_JD }));

  const runAlignment = async () => {
    if (!state.jobDescription) return;
    startLoading('Analyzing job alignment...', ['Parsing job description', 'Matching skills', 'Calculating fit score', 'Generating insights']);
    try {
      updateProgress(25, 0);
      const report = await alignmentAgent(state.currentResume, state.jobDescription);
      updateProgress(100, 3);
      setState(prev => ({ ...prev, alignmentReport: report, status: WorkflowStatus.AWAITING_ALIGNMENT_APPROVAL }));
    } catch (err: any) {
      setError(err.message);
    } finally {
      stopLoading();
    }
  };

  const startInterviewSelection = () => {
    setState(prev => ({
      ...prev,
      status: WorkflowStatus.SELECTING_INTERVIEW_MODE,
      interviewHistory: [],
    }));
  };

  const startInterview = async (mode: InterviewMode) => {
    setState(prev => ({
      ...prev,
      interviewMode: mode,
      status: WorkflowStatus.INTERVIEWING,
      interviewHistory: [],
    }));

    if (mode === 'VOICE') {
      setError(null);
      return; // Handled by WebSocket auto-start
    }

    startLoading('Starting interview...', ['Preparing first question', 'Personalizing coach guidance']);
    setError(null);
    try {
      updateProgress(50, 0);
      const openingQuestion = await backendService.interviewCoachAgent(
        state.currentResume,
        state.jobDescription,
        [],
      );
      updateProgress(100, 1);
      setState(prev => ({
        ...prev,
        status: WorkflowStatus.INTERVIEWING,
        interviewHistory: [{ role: 'agent', text: openingQuestion }],
      }));
    } catch (err: any) {
      setError(err.message);
      setState(prev => ({
        ...prev,
        status: WorkflowStatus.SELECTING_INTERVIEW_MODE,
        interviewHistory: [],
      }));
    } finally {
      stopLoading();
    }
  };

  const handleInterviewMessage = async (msg: string) => {
    const updatedHistory = [...state.interviewHistory, { role: 'user' as const, text: msg }];
    setState(prev => ({ ...prev, interviewHistory: updatedHistory }));
    startLoading('Coach is thinking...', ['Analyzing your response', 'Generating feedback']);
    try {
      updateProgress(50, 0);
      const responseText = await backendService.interviewCoachAgent(
        state.currentResume,
        state.jobDescription,
        updatedHistory,
      );
      const interviewComplete = isInterviewCompleteResponse(responseText);
      updateProgress(100, 1);
      setState(prev => ({
        ...prev,
        interviewHistory: [...updatedHistory, { role: 'agent', text: responseText }],
        status: interviewComplete ? WorkflowStatus.COMPLETED : prev.status,
      }));
    } catch (err: any) {
      setError(err.message);
    } finally {
      stopLoading();
    }
  };

  const handleInterviewAudioMessage = async (audio: Uint8Array) => {
    // This is the legacy audio path used only in CHAT mode for voice-to-text
    const updatedHistory = [...state.interviewHistory, { role: 'user' as const, text: '[Analyzing audio...]' }];
    setState(prev => ({ ...prev, interviewHistory: updatedHistory }));
    
    try {
      const request: ChatRequest = {
        intent: 'INTERVIEW_COACH',
        resumeData: state.currentResume,
        jobDescription: state.jobDescription,
        messageHistory: updatedHistory,
        audioData: audio,
      };
      
      const response = await backendService.callChatEndpoint(request);
      const responseText = backendService.formatInterviewCoachPayload(response.payload ?? response.content);
      const interviewComplete = isInterviewCompleteResponse(responseText);
      
      setState(prev => {
        const newHistory = prev.interviewHistory.map((msg, i) => 
          i === prev.interviewHistory.length - 1 && msg.text === '[Analyzing audio...]' 
            ? { ...msg, text: (response as any).transcription || '[Audio response]' } 
            : msg
        );
        return {
          ...prev,
          interviewHistory: [...newHistory, { role: 'agent', text: responseText }],
          status: interviewComplete ? WorkflowStatus.COMPLETED : prev.status,
        };
      });
    } catch (err: any) {
      setError(err.message || 'Failed to process audio');
      setState(prev => ({
        ...prev,
        interviewHistory: prev.interviewHistory.filter(msg => msg.text !== '[Analyzing audio...]')
      }));
    }
  };

  const handleLiveEvent = (event: { type: string; text?: string }) => {
    if (event.type === 'user' && event.text) {
      setState(prev => {
        const history = [...prev.interviewHistory];
        const last = history[history.length - 1];
        if (last && last.role === 'user') {
          // If the last message was also from user, we might be getting streaming updates
          // For simplicity in this UI, we just append or replace
          return { ...prev, interviewHistory: [...history.slice(0, -1), { role: 'user', text: event.text || '' }] };
        }
        return { ...prev, interviewHistory: [...history, { role: 'user', text: event.text || '' }] };
      });
    } else if (event.type === 'gemini' && event.text) {
      setState(prev => {
        const history = [...prev.interviewHistory];
        const last = history[history.length - 1];
        if (last && last.role === 'agent') {
          return { ...prev, interviewHistory: [...history.slice(0, -1), { role: 'agent', text: event.text || '' }] };
        }
        return { ...prev, interviewHistory: [...history, { role: 'agent', text: event.text || '' }] };
      });
    }
  };

  return (
    <>
      {(state.status === WorkflowStatus.IDLE || state.status === WorkflowStatus.EXTRACTING) && (
        <UploadStep
          onUploadSubmit={handleUploadSubmit}
          reviewNotice={state.extractionReview}
          reviewPayload={state.extractionReview?.reviewPayload}
          manualResumeText={manualResumeText}
          manualResumeError={manualResumeError}
          onManualResumeChange={setManualResumeText}
          onManualSubmit={submitManualResume}
          onReviewSubmit={submitReviewResume}
        />
      )}
      {(state.status === WorkflowStatus.CRITIQUING || state.status === WorkflowStatus.AWAITING_CRITIC_APPROVAL) && state.criticReport && (
        <CriticStep report={state.criticReport} resume={state.currentResume} onApprove={approveCritic} />
      )}
      {(state.status === WorkflowStatus.ANALYZING_CONTENT || state.status === WorkflowStatus.AWAITING_CONTENT_APPROVAL) && state.contentReport && (
        <ContentStep report={state.contentReport} resume={state.currentResume} onApprove={approveContent} />
      )}
      {(state.status === WorkflowStatus.ALIGNING_JD) && <AlignmentStep jd={state.jobDescription} onChangeJD={(val) => setState(prev => ({ ...prev, jobDescription: val }))} onAnalyze={runAlignment} isLoading={false} />}
      {(state.status === WorkflowStatus.AWAITING_ALIGNMENT_APPROVAL) && state.alignmentReport && (
        <AlignmentReportStep
          report={state.alignmentReport}
          resume={state.currentResume}
          onStartInterview={startInterviewSelection}
        />
      )}
      {(state.status === WorkflowStatus.SELECTING_INTERVIEW_MODE) && <InterviewModeSelectionStep onSelect={startInterview} />}
      {(state.status === WorkflowStatus.INTERVIEWING || state.status === WorkflowStatus.DEBUG_VOICE || state.status === WorkflowStatus.COMPLETED) && (
        <InterviewStep 
          history={state.interviewHistory} 
          onSend={handleInterviewMessage} 
          onSendAudio={handleInterviewAudioMessage} 
          isLoading={false} 
          chatEndRef={chatEndRef} 
          mode={state.status === WorkflowStatus.DEBUG_VOICE ? 'VOICE' : (state.interviewMode || 'CHAT')} 
          sessionId={backendService.getSessionId()} 
          isComplete={state.status === WorkflowStatus.COMPLETED}
          onExit={() => setState(prev => ({ ...prev, status: WorkflowStatus.SELECTING_INTERVIEW_MODE }))}
          onLiveEvent={handleLiveEvent}
        />
      )}
    </>
  );
};

// Loading wrapper component
const LoadingStateWrapper: React.FC = () => {
  const { isLoading, message, progress, steps, currentStep } = useLoading();
  
  return <LoadingState 
    isLoading={isLoading} 
    message={message} 
    progress={progress} 
    steps={steps} 
    currentStep={currentStep} 
  />;
};

// Main App component with provider
const App: React.FC = () => {
  return (
    <LoadingProvider>
      <AppContent />
    </LoadingProvider>
  );
};

export default App;
