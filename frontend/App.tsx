import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  SharedState, 
  WorkflowStatus,
  ChatRequest,
  Resume
} from './types';
import {
  contentStrengthAgent, 
  alignmentAgent, 
  interviewCoachAgent,
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
  InterviewStep 
} from './components/WorkflowSteps';

const AppContent: React.FC = () => {
  const [state, setState] = useState<SharedState>(() => {
    const saved = localStorage.getItem('interview_ready_state');
    if (saved) return JSON.parse(saved);
    return {
      currentResume: null,
      history: [],
      jobDescription: '',
      status: WorkflowStatus.IDLE,
      criticReport: null,
      contentReport: null,
      alignmentReport: null,
      interviewHistory: []
    };
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    localStorage.setItem('interview_ready_state', JSON.stringify(state));
  }, [state]);

  const resetSession = useCallback(() => {
    if (confirm('Reset current progress? This will clear all data and start over.')) {
      localStorage.removeItem('interview_ready_state');
      setState({
        currentResume: null,
        history: [],
        jobDescription: '',
        status: WorkflowStatus.IDLE,
        criticReport: null,
        contentReport: null,
        alignmentReport: null,
        interviewHistory: []
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

  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

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

  const normalizeCriticReport = (data: any) => {
    const candidate = data && typeof data === 'object' ? (data.critique ?? data) : {};
    const issues = Array.isArray(candidate.issues)
        ? candidate.issues
        : [];
    return {
      issueList: issues,
      summary: typeof candidate.summary === 'string' && candidate.summary.trim()
        ? candidate.summary
        : 'Resume processed successfully.',
      score: typeof candidate.score === 'number' ? candidate.score : undefined
    };
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    console.log('handleFileupload')
    const file = e.target.files?.[0];
    if (!file) return;

    setIsLoading(true);
    setError(null);
    try {
      if (file.type === 'application/pdf') {
        const base64 = await fileToBase64(file);

        const request: ChatRequest = {
          intent: 'RESUME_CRITIC',
          resumeData: null,
          jobDescription: '',
          messageHistory: [],
          resumeFile: { data: base64, fileType: 'pdf' }
        };
        
        const response = await backendService.callChatEndpoint(request);
        const parsedResume = await backendService.fetchCurrentResume();
        // Parse the structured JSON response from backend
        let responseData;
        try {
          responseData = response.payload || JSON.parse(response.content || '{}');
        } catch (error) {
          console.error('Failed to parse backend response:', error);
          throw new Error('Invalid response from backend');
        }

        const resumeData = responseData.resume_data || {};
        const criticReport = normalizeCriticReport(
          response.payload && typeof response.payload === 'object' && !Array.isArray(response.payload)
            ? response.payload
            : responseData
        );

        setState(prev => ({
          ...prev,
          currentResume: parsedResume || prev.currentResume,
          history: parsedResume ? [...prev.history, parsedResume] : prev.history,
          criticReport,
          status: WorkflowStatus.AWAITING_CRITIC_APPROVAL
        }));
      } else {
        setError("Only PDF files are supported.")
      }
    } catch (err: any) {
      setError(err.message || "Failed to process resume");
    } finally {
      setIsLoading(false);
    }
  };

  const approveCritic = async () => {
    setState(prev => ({ ...prev, status: WorkflowStatus.ANALYZING_CONTENT }));
    setIsLoading(true);
    try {
      const report = await contentStrengthAgent(state.currentResume);
      setState(prev => ({ ...prev, contentReport: report, status: WorkflowStatus.AWAITING_CONTENT_APPROVAL }));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const approveContent = () => setState(prev => ({ ...prev, status: WorkflowStatus.ALIGNING_JD }));

  const runAlignment = async () => {
    if (!state.jobDescription) return;
    setIsLoading(true);
    try {
      const report = await alignmentAgent(state.currentResume, state.jobDescription);
      setState(prev => ({ ...prev, alignmentReport: report, status: WorkflowStatus.AWAITING_ALIGNMENT_APPROVAL }));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const startInterview = async () => {
    setState(prev => ({ 
      ...prev, 
      status: WorkflowStatus.INTERVIEWING, 
      interviewHistory: [{ role: 'agent', text: "Ready to practice? Based on your profile, tell me why you're a fit for this role." }]
    }));
  };

  const handleInterviewMessage = async (msg: string) => {
    const updatedHistory = [...state.interviewHistory, { role: 'user' as const, text: msg }];
    setState(prev => ({ ...prev, interviewHistory: updatedHistory }));
    setIsLoading(true);
    try {
      const responseText = await interviewCoachAgent(state.alignmentReport, updatedHistory);
      setState(prev => ({ ...prev, interviewHistory: [...updatedHistory, { role: 'agent', text: responseText }] }));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleInterviewAudioMessage = async (audio: Uint8Array) => {
    const updatedHistory = [...state.interviewHistory, { role: 'user' as const, text: '[Audio response]' }];
    setState(prev => ({ ...prev, interviewHistory: updatedHistory }));
    setIsLoading(true);
    try {
      const request: ChatRequest = {
        intent: 'INTERVIEW_COACH',
        resumeData: state.currentResume,
        jobDescription: state.jobDescription,
        messageHistory: updatedHistory,
        audioData: audio,
      };
      const response = await backendService.callChatEndpoint(request);
      const responseText = typeof response.payload === 'string' ? response.payload : JSON.stringify(response.payload);
      setState(prev => ({ ...prev, interviewHistory: [...updatedHistory, { role: 'agent', text: responseText }] }));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

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
          <div className="h-4 w-[1px] bg-slate-200"></div>
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
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3 text-red-700 animate-in fade-in slide-in-from-top-1">
                <div className="mt-0.5 text-red-500">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" /></svg>
                </div>
                <div className="text-xs font-medium">{error}</div>
              </div>
            )}

            <div className="relative">
              <WorkflowController 
                state={state} 
                setState={setState} 
                setError={setError}
                chatEndRef={chatEndRef}
              />
            </div>
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

          {state.history.length > 1 && state.status === WorkflowStatus.IDLE && (
            <div className="absolute top-6 right-6 group">
              <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-sm w-64 max-h-[300px] overflow-y-auto">
                 <h4 className="text-[10px] font-bold text-slate-400 uppercase mb-3">Recent Uploads</h4>
                 <div className="space-y-1.5">
                   {state.history.map((h, index) => (
                     <button 
                       key={index}
                       onClick={() => setState(prev => ({ ...prev, currentResume: h, status: WorkflowStatus.CRITIQUING }))}
                       className="w-full p-2.5 rounded-lg text-left text-[11px] font-medium text-slate-600 hover:bg-slate-50 border border-transparent hover:border-slate-200 transition-all truncate"
                     >
                        Resume {index + 1}
                     </button>
                   ))}
                 </div>
              </div>
            </div>
          )}
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

  const MAX_FILE_SIZE = 10 * 1024 * 1024;

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

  const normalizeCriticReport = (data: any) => {
    const candidate = data && typeof data === 'object' ? (data.critique ?? data) : {};
    const issues = Array.isArray(candidate.issues)
        ? candidate.issues
        : [];
    return {
      issueList: issues,
      summary: typeof candidate.summary === 'string' && candidate.summary.trim()
        ? candidate.summary
        : 'Resume processed successfully.',
      score: typeof candidate.score === 'number' ? candidate.score : undefined
    };
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    startLoading('Analyzing your resume...', ['Uploading file', 'Extracting content', 'Analyzing structure', 'Generating insights']);
    setError(null);
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
        const critiqueData =
          response.payload && typeof response.payload === 'object' && !Array.isArray(response.payload)
            ? response.payload
            : {};

        let responseData;
        try {
          responseData = response.payload || JSON.parse(response.content || '{}');
        } catch (error) {
          console.error('Failed to parse backend response:', error);
          throw new Error('Invalid response from backend');
        }

        const resumeData = responseData.resume_data || {};

        const resume = {
          title: resumeData.title || 'Untitled Resume',
          summary: resumeData.summary || '',
          isMaster: false,
          contact: resumeData.contact || {
            fullName: '',
            email: '',
            phone: '',
            city: '',
            country: '',
            linkedin: '',
            github: '',
            portfolio: ''
          },
          skills: resumeData.skills || [],
          experience: resumeData.experiences || resumeData.experience || [],
          education: resumeData.educations || resumeData.education || [],
          experiences: resumeData.experiences || resumeData.experience || [],
          educations: resumeData.educations || resumeData.education || [],
          projects: resumeData.projects || [],
          certifications: resumeData.certifications || [],
          awards: resumeData.awards || []
        };

        updateProgress(90, 3);

        const criticReport = normalizeCriticReport(
          response.payload && typeof response.payload === 'object' && !Array.isArray(response.payload)
            ? response.payload
            : responseData
        );

        setState(prev => ({
          ...prev,
          currentResume: parsedResume || prev.currentResume,
          history: parsedResume ? [...prev.history, parsedResume] : prev.history,
          criticReport,
          status: WorkflowStatus.AWAITING_CRITIC_APPROVAL
        }));
        updateProgress(100, 3);
      }
    } catch (err: any) {
      setError(err.message || "Failed to process resume");
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

  const startInterview = async () => {
    setState(prev => ({ 
      ...prev, 
      status: WorkflowStatus.INTERVIEWING, 
      interviewHistory: [{ role: 'agent', text: "Ready to practice? Based on your profile, tell me why you're a fit for this role." }]
    }));
  };

  const handleInterviewMessage = async (msg: string) => {
    const updatedHistory = [...state.interviewHistory, { role: 'user' as const, text: msg }];
    setState(prev => ({ ...prev, interviewHistory: updatedHistory }));
    startLoading('Coach is thinking...', ['Analyzing your response', 'Generating feedback']);
    try {
      updateProgress(50, 0);
      const responseText = await interviewCoachAgent(state.alignmentReport, updatedHistory);
      updateProgress(100, 1);
      setState(prev => ({ ...prev, interviewHistory: [...updatedHistory, { role: 'agent', text: responseText }] }));
    } catch (err: any) {
      setError(err.message);
    } finally {
      stopLoading();
    }
  };

  const handleInterviewAudioMessage = async (audio: Uint8Array) => {
    const updatedHistory = [...state.interviewHistory, { role: 'user' as const, text: '[Audio response]' }];
    setState(prev => ({ ...prev, interviewHistory: updatedHistory }));
    startLoading('Processing audio...', ['Transcribing speech', 'Analyzing content', 'Generating response']);
    try {
      updateProgress(33, 0);
      const request: ChatRequest = {
        intent: 'INTERVIEW_COACH',
        resumeData: state.currentResume,
        jobDescription: state.jobDescription,
        messageHistory: updatedHistory,
        audioData: audio,
      };
      updateProgress(66, 1);
      const response = await backendService.callChatEndpoint(request);
      const responseText = typeof response.payload === 'string' ? response.payload : JSON.stringify(response.payload);
      updateProgress(100, 2);
      setState(prev => ({ ...prev, interviewHistory: [...updatedHistory, { role: 'agent', text: responseText }] }));
    } catch (err: any) {
      setError(err.message);
    } finally {
      stopLoading();
    }
  };

  return (
    <>
      {(state.status === WorkflowStatus.IDLE || state.status === WorkflowStatus.EXTRACTING) && <UploadStep onUpload={handleFileUpload} />}
      {(state.status === WorkflowStatus.CRITIQUING || state.status === WorkflowStatus.AWAITING_CRITIC_APPROVAL) && state.criticReport && <CriticStep report={state.criticReport} onApprove={approveCritic} />}
      {(state.status === WorkflowStatus.ANALYZING_CONTENT || state.status === WorkflowStatus.AWAITING_CONTENT_APPROVAL) && state.contentReport && <ContentStep report={state.contentReport} onApprove={approveContent} />}
      {(state.status === WorkflowStatus.ALIGNING_JD) && <AlignmentStep jd={state.jobDescription} onChangeJD={(val) => setState(prev => ({ ...prev, jobDescription: val }))} onAnalyze={runAlignment} isLoading={false} />}
      {(state.status === WorkflowStatus.AWAITING_ALIGNMENT_APPROVAL) && state.alignmentReport && <AlignmentReportStep report={state.alignmentReport} onStartInterview={startInterview} />}
      {state.status === WorkflowStatus.INTERVIEWING && <InterviewStep history={state.interviewHistory} onSend={handleInterviewMessage} onSendAudio={handleInterviewAudioMessage} isLoading={false} chatEndRef={chatEndRef} />}
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
