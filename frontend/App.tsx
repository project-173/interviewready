
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  SharedState, 
  WorkflowStatus, 
  Resume
} from './types';
import { 
  extractorAgent, 
  resumeCriticAgent, 
  contentStrengthAgent, 
  alignmentAgent, 
  interviewCoachAgent 
} from './geminiService';
import { StepIndicator } from './components/StepIndicator';
import { ResumePreview } from './components/ResumePreview';
import { 
  UploadStep, 
  CriticStep, 
  ContentStep, 
  AlignmentStep, 
  AlignmentReportStep, 
  InterviewStep 
} from './components/WorkflowSteps';

const App: React.FC = () => {
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
    let canNavigate = false;

    if (status === WorkflowStatus.IDLE) canNavigate = true;
    if (status === WorkflowStatus.CRITIQUING && state.currentResume) canNavigate = true;
    if (status === WorkflowStatus.ANALYZING_CONTENT && state.criticReport) canNavigate = true;
    if (status === WorkflowStatus.ALIGNING_JD && state.contentReport) canNavigate = true;
    if (status === WorkflowStatus.INTERVIEWING && state.alignmentReport) canNavigate = true;

    if (canNavigate) {
      let targetStatus = status;
      if (status === WorkflowStatus.CRITIQUING && state.criticReport) {
        targetStatus = WorkflowStatus.AWAITING_CRITIC_APPROVAL;
      } else if (status === WorkflowStatus.ANALYZING_CONTENT && state.contentReport) {
        targetStatus = WorkflowStatus.AWAITING_CONTENT_APPROVAL;
      } else if (status === WorkflowStatus.ALIGNING_JD && state.alignmentReport) {
        targetStatus = WorkflowStatus.AWAITING_ALIGNMENT_APPROVAL;
      }

      setState(prev => ({ ...prev, status: targetStatus }));
    }
  }, [state.currentResume, state.criticReport, state.contentReport, state.alignmentReport]);

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve((reader.result as string).split(',')[1]);
      reader.onerror = reject;
    });
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsLoading(true);
    setError(null);
    try {
      if (file.type === 'application/pdf') {
        const base64 = await fileToBase64(file);
        const schema = await extractorAgent({ data: base64, mimeType: file.type });
        processExtractedResume(schema);
      } else {
        const reader = new FileReader();
        reader.onload = async (event) => {
          const schema = await extractorAgent(event.target?.result as string);
          processExtractedResume(schema);
        };
        reader.readAsText(file);
      }
    } catch (err: any) {
      setError(err.message || "Failed to process resume");
    } finally {
      setIsLoading(false);
    }
  };

  const processExtractedResume = (schema: Resume) => {
    setState(prev => ({ 
      ...prev, 
      currentResume: schema, 
      history: [...prev.history, schema],
      status: WorkflowStatus.CRITIQUING 
    }));
    runCritic(schema);
  };

  const runCritic = async (resume: Resume) => {
    setIsLoading(true);
    try {
      const report = await resumeCriticAgent(resume);
      setState(prev => ({ ...prev, criticReport: report, status: WorkflowStatus.AWAITING_CRITIC_APPROVAL }));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const approveCritic = async () => {
    setState(prev => ({ ...prev, status: WorkflowStatus.ANALYZING_CONTENT }));
    setIsLoading(true);
    try {
      const report = await contentStrengthAgent(state.currentResume!);
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
      const report = await alignmentAgent(state.currentResume!, state.jobDescription);
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
      const responseText = await interviewCoachAgent(state.alignmentReport!, updatedHistory);
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

            {isLoading && state.status !== WorkflowStatus.INTERVIEWING && (
              <div className="flex items-center gap-3 p-4 bg-slate-50 border border-slate-200 rounded-lg animate-pulse">
                <div className="w-3 h-3 border-2 border-slate-400 border-t-transparent rounded-full animate-spin"></div>
                <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-widest">Agent processing...</span>
              </div>
            )}

            <div className="relative">
              {(state.status === WorkflowStatus.IDLE || state.status === WorkflowStatus.EXTRACTING) && <UploadStep onUpload={handleFileUpload} />}
              {(state.status === WorkflowStatus.CRITIQUING || state.status === WorkflowStatus.AWAITING_CRITIC_APPROVAL) && state.criticReport && <CriticStep report={state.criticReport} onApprove={approveCritic} />}
              {(state.status === WorkflowStatus.ANALYZING_CONTENT || state.status === WorkflowStatus.AWAITING_CONTENT_APPROVAL) && state.contentReport && <ContentStep report={state.contentReport} onApprove={approveContent} />}
              {(state.status === WorkflowStatus.ALIGNING_JD) && <AlignmentStep jd={state.jobDescription} onChangeJD={(val) => setState(prev => ({ ...prev, jobDescription: val }))} onAnalyze={runAlignment} isLoading={isLoading} />}
              {(state.status === WorkflowStatus.AWAITING_ALIGNMENT_APPROVAL) && state.alignmentReport && <AlignmentReportStep report={state.alignmentReport} onStartInterview={startInterview} />}
              {state.status === WorkflowStatus.INTERVIEWING && <InterviewStep history={state.interviewHistory} onSend={handleInterviewMessage} isLoading={isLoading} chatEndRef={chatEndRef} />}
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
                   {state.history.map((h, i) => (
                     <button 
                       key={i} 
                       onClick={() => setState(prev => ({ ...prev, currentResume: h, status: WorkflowStatus.CRITIQUING }))}
                       className="w-full p-2.5 rounded-lg text-left text-[11px] font-medium text-slate-600 hover:bg-slate-50 border border-transparent hover:border-slate-200 transition-all truncate"
                     >
                        {h.contact?.fullName || 'Untitled Resume'}
                     </button>
                   ))}
                 </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
