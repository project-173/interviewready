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
    this.sessionId = this.generateSessionId();
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
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
      return JSON.parse(response.content || '{}');
    } catch (error) {
      console.error('Failed to parse resume critic response:', error);
      throw new Error('Invalid response from resume critic agent');
    }
  }

  async contentStrengthAgent(resume: Resume): Promise<ContentAnalysisReport> {
    const request: ChatRequest = {
      intent: 'CONTENT_STRENGTH',
      resumeData: resume,
      jobDescription: '',
      messageHistory: []
    };
    
    const response = await this.callChatEndpoint(request);
    
    try {
      return JSON.parse(response.content || '{}');
    } catch (error) {
      console.error('Failed to parse content strength response:', error);
      throw new Error('Invalid response from content strength agent');
    }
  }

  async alignmentAgent(resume: Resume, jd: string): Promise<AlignmentReport> {
    const request: ChatRequest = {
      intent: 'ALIGNMENT',
      resumeData: resume,
      jobDescription: jd,
      messageHistory: []
    };
    
    const response = await this.callChatEndpoint(request);
    
    try {
      const data = JSON.parse(response.content || '{}');
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
    history: { role: 'user' | 'agent'; text: string }[]
  ): Promise<string> {
    // Create a minimal resume object for the interview coach
    const resume: Resume = {
      title: '',
      summary: '',
      isMaster: false,
      contact: {
        fullName: '',
        email: '',
        phone: '',
        city: '',
        country: '',
        linkedin: '',
        github: '',
        portfolio: ''
      },
      skills: [],
      experiences: [],
      educations: [],
      projects: [],
      certifications: [],
      awards: []
    };

    const request: ChatRequest = {
      intent: 'INTERVIEW_COACH',
      resumeData: resume,
      jobDescription: JSON.stringify(alignment),
      messageHistory: history
    };
    
    const response = await this.callChatEndpoint(request);
    return response.content || "I'm sorry, I couldn't generate a response.";
  }
}

export const backendService = new BackendService();

// Export individual functions for backward compatibility
export const resumeCriticAgent = (resume: Resume) => backendService.resumeCriticAgent(resume);
export const contentStrengthAgent = (resume: Resume) => backendService.contentStrengthAgent(resume);
export const alignmentAgent = (resume: Resume, jd: string) => backendService.alignmentAgent(resume, jd);
export const interviewCoachAgent = (alignment: AlignmentReport, history: { role: 'user' | 'agent'; text: string }[]) => backendService.interviewCoachAgent(alignment, history);
