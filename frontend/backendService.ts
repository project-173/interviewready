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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

if (!API_BASE_URL) {
  console.warn("VITE_API_BASE_URL is not defined, falling back to empty string for relative paths or development");
}

export interface ExtractorFileData {
  data: string;
  mimeType: string;
}

interface ChatResponse {
  agent?: string;
  payload?: any;
  agent_name?: string;
  content?: string;
  reasoning?: string;
  confidence_score?: number;
  decision_trace?: string[];
  sharp_metadata?: Record<string, any>;
}

class BackendService {
  private sessionId: string;

  constructor() {
    // Persist session ID across page reloads so the backend can retain session-scoped state
    const storedSessionId = localStorage.getItem('interviewready_session_id');
    if (storedSessionId) {
      this.sessionId = storedSessionId;
    } else {
      this.sessionId = this.generateSessionId();
      localStorage.setItem('interviewready_session_id', this.sessionId);
    }
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
    const requestBody = {
      ...request,
      audioData: request.audioData ? btoa(String.fromCharCode(...request.audioData)) : null,
    };
    const response = await fetch(`${API_BASE_URL}/api/v1/chat?sessionId=${this.sessionId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAuthToken()}`,
      },
      body: JSON.stringify(requestBody),
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
    
    try {
      if (response.payload && typeof response.payload === 'object') {
        return response.payload;
      }
      return JSON.parse(response.content || '{}');
    } catch (error) {
      console.error('Failed to parse resume critic response:', error);
      throw new Error('Invalid response from resume critic agent');
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
    
    try {
      if (response.payload && typeof response.payload === 'object') {
        return response.payload;
      }
      return JSON.parse(response.content || '{}');
    } catch (error) {
      console.error('Failed to parse content strength response:', error);
      throw new Error('Invalid response from content strength agent');
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
    
    try {
      let data = response.payload;
      if (!data || typeof data !== 'object') {
        data = JSON.parse(response.content || '{}');
      }
      return {
        ...data,
        sources: data.sources || []
      };
    } catch (error) {
      console.error('Failed to parse alignment response:', error);
      throw new Error('Invalid response from alignment agent');
    }
  }

  async interviewCoachAgent(
    alignment: AlignmentReport,
    history: { role: 'user' | 'agent'; text: string }[],
    resume?: Resume | null,
    jobDescription?: string
  ): Promise<string> {
    const request: ChatRequest = {
      intent: 'INTERVIEW_COACH',
      resumeData: resume ?? null,
      jobDescription: jobDescription || JSON.stringify(alignment),
      messageHistory: history,
    };

    const response = await this.callChatEndpoint(request);
    // The backend returns `payload` (not `content`) for chat responses.
    // Use it directly if it's a string; otherwise serialize objects to show something meaningful.
    if (typeof response.payload === 'string') {
      return response.payload;
    }
    if (response.payload && typeof response.payload === 'object') {
      return JSON.stringify(response.payload, null, 2);
    }
    return "I'm sorry, I couldn't generate a response.";
  }
}

export const backendService = new BackendService();

// Export individual functions for backward compatibility
export const resumeCriticAgent = (resume: Resume) => backendService.resumeCriticAgent(resume);
export const contentStrengthAgent = (resume?: Resume | null) => backendService.contentStrengthAgent(resume);
export const alignmentAgent = (resume: Resume | null | undefined, jd: string) => backendService.alignmentAgent(resume, jd);
export const interviewCoachAgent = (
  alignment: AlignmentReport,
  history: { role: 'user' | 'agent'; text: string }[],
  resume?: Resume | null,
  jobDescription?: string
) => backendService.interviewCoachAgent(alignment, history, resume, jobDescription);
