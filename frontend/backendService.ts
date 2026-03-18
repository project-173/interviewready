import { 
  Resume, 
  StructuralAssessment, 
  ContentAnalysisReport, 
  AlignmentReport,
  ChatRequest,
  resumeJsonSchema,
  structuralAssessmentJsonSchema,
  contentAnalysisReportJsonSchema,
  alignmentReportJsonSchema
} from './types';

const API_BASE_URL = import.meta.env.VITE_APP_API_URL;

if (!API_BASE_URL) {
  throw new Error("API_BASE_URL is not defined")
}

export interface ExtractorFileData {
  data: string;
  mimeType: string;
}

interface ChatResponse {
  agent?: string;
  payload?: Record<string, any> | any[] | string;
}

class BackendService {
  private sessionId: string;

  constructor() {
    this.sessionId = this.generateSessionId();
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private hasResumeContent(resume?: Resume | null): boolean {
    if (!resume) return false;
    return Object.values(resume).some((value) => {
      if (Array.isArray(value)) {
        return value.length > 0;
      }
      return Boolean(value);
    });
  }

  getSessionId(): string {
    return this.sessionId;
  }

  async callChatEndpoint(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat?sessionId=${this.sessionId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAuthToken()}`,
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Backend API error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  }

  async fetchCurrentResume(): Promise<Resume | null> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/sessions/${this.sessionId}/resume`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.getAuthToken()}`,
        },
      }
    );

    if (response.status === 404) {
      return null;
    }
    if (!response.ok) {
      throw new Error(`Backend API error: ${response.status} ${response.statusText}`);
    }

    return (await response.json()) as Resume;
  }

  private getAuthToken(): string {
    // This should be implemented based on your auth strategy
    // For now, returning a placeholder
    return localStorage.getItem('authToken') || '';
  }

  async resumeCriticAgent(resume: Resume): Promise<StructuralAssessment> {
    const request: ChatRequest = {
      intent: 'RESUME_CRITIC',
      resumeData: resume,
      jobDescription: '',
      messageHistory: []
    };
    
    const response = await this.callChatEndpoint(request);
    const payload = response.payload;
    if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
      return payload as StructuralAssessment;
    }
    throw new Error('Invalid response from resume critic agent');
  }

  async contentStrengthAgent(resume?: Resume | null): Promise<ContentAnalysisReport> {
    const request: ChatRequest = {
      intent: 'CONTENT_STRENGTH',
      jobDescription: '',
      messageHistory: []
    };
    if (this.hasResumeContent(resume)) request.resumeData = resume;
    
    const response = await this.callChatEndpoint(request);
    const payload = response.payload;
    if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
      return payload as ContentAnalysisReport;
    }
    throw new Error('Invalid response from content strength agent');
  }

  async alignmentAgent(resume: Resume | null | undefined, jd: string): Promise<AlignmentReport> {
    const request: ChatRequest = {
      intent: 'ALIGNMENT',
      jobDescription: jd,
      messageHistory: []
    };
    if (this.hasResumeContent(resume)) request.resumeData = resume;
    
    const response = await this.callChatEndpoint(request);
    const payload = response.payload;
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      throw new Error('Invalid response from alignment agent');
    }
    const data = payload as Record<string, any>;
    return {
      ...data,
      sources: data.sources || []
    } as AlignmentReport;
  }

  async interviewCoachAgent(
    alignment: AlignmentReport, 
    history: { role: 'user' | 'agent'; text: string }[]
  ): Promise<string> {
    const resume: Resume = {
      work: [],
      education: [],
      awards: [],
      certificates: [],
      skills: [],
      projects: []
    };

    const request: ChatRequest = {
      intent: 'INTERVIEW_COACH',
      resumeData: resume,
      jobDescription: JSON.stringify(alignment),
      messageHistory: history
    };
    
    const response = await this.callChatEndpoint(request);
    return typeof response.payload === 'string'
      ? response.payload
      : "I'm sorry, I couldn't generate a response.";
  }
}

export const backendService = new BackendService();

// Export individual functions for backward compatibility
export const resumeCriticAgent = (resume: Resume) => backendService.resumeCriticAgent(resume);
export const contentStrengthAgent = (resume?: Resume | null) => backendService.contentStrengthAgent(resume);
export const alignmentAgent = (resume: Resume | null | undefined, jd: string) => backendService.alignmentAgent(resume, jd);
export const interviewCoachAgent = (alignment: AlignmentReport, history: { role: 'user' | 'agent'; text: string }[]) => backendService.interviewCoachAgent(alignment, history);
