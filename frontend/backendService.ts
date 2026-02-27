import { 
  Resume, 
  StructuralAssessment, 
  ContentAnalysisReport, 
  AlignmentReport,
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

  private async callChatEndpoint(message: string): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat?sessionId=${this.sessionId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAuthToken()}`,
      },
      body: JSON.stringify({ message }),
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

  async extractorAgent(input: string | ExtractorFileData): Promise<Resume> {
    let message: string;
    
    if (typeof input === 'string') {
      message = `EXTRACTOR: Parse the following resume text into a structured JSON format. Resume Text: ${input}`;
    } else {
      message = `EXTRACTOR: Parse the attached resume file into a structured JSON format. File data: ${input.data}, MIME type: ${input.mimeType}`;
    }

    const response = await this.callChatEndpoint(message);
    
    try {
      const data = JSON.parse(response.content || '{}');
      return {
        title: data.title || 'Untitled Resume',
        summary: data.summary || '',
        isMaster: false,
        contact: data.contact || {
          fullName: '',
          email: '',
          phone: '',
          city: '',
          country: '',
          linkedin: '',
          github: '',
          portfolio: ''
        },
        skills: data.skills || [],
        experiences: data.experiences || [],
        educations: data.educations || [],
        projects: data.projects || [],
        certifications: data.certifications || [],
        awards: data.awards || []
      };
    } catch (error) {
      console.error('Failed to parse extractor response:', error);
      throw new Error('Invalid response from extractor agent');
    }
  }

  async resumeCriticAgent(resume: Resume): Promise<StructuralAssessment> {
    const message = `RESUME_CRITIC: Critique the structure and formatting of this resume: ${JSON.stringify(resume)}`;
    
    const response = await this.callChatEndpoint(message);
    
    try {
      return JSON.parse(response.content || '{}');
    } catch (error) {
      console.error('Failed to parse resume critic response:', error);
      throw new Error('Invalid response from resume critic agent');
    }
  }

  async contentStrengthAgent(resume: Resume): Promise<ContentAnalysisReport> {
    const message = `CONTENT_STRENGTH: Analyze the content strength and skills of this resume using STAR/XYZ methodology: ${JSON.stringify(resume)}`;
    
    const response = await this.callChatEndpoint(message);
    
    try {
      return JSON.parse(response.content || '{}');
    } catch (error) {
      console.error('Failed to parse content strength response:', error);
      throw new Error('Invalid response from content strength agent');
    }
  }

  async alignmentAgent(resume: Resume, jd: string): Promise<AlignmentReport> {
    const message = `ALIGNMENT: Analyze the fit between this resume and the Job Description. Use Google Search to research the company or specific technology trends if necessary.
    Resume: ${JSON.stringify(resume)}
    JD: ${jd}`;
    
    const response = await this.callChatEndpoint(message);
    
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
    const message = `INTERVIEW_COACH: You are a high-stakes Interview Coach. Based on this alignment report: ${JSON.stringify(alignment)}, conduct a realistic mock interview. Ask one targeted question at a time. History: ${JSON.stringify(history)}`;
    
    const response = await this.callChatEndpoint(message);
    return response.content || "I'm sorry, I couldn't generate a response.";
  }
}

export const backendService = new BackendService();

// Export individual functions for backward compatibility
export const extractorAgent = (input: string | ExtractorFileData) => backendService.extractorAgent(input);
export const resumeCriticAgent = (resume: Resume) => backendService.resumeCriticAgent(resume);
export const contentStrengthAgent = (resume: Resume) => backendService.contentStrengthAgent(resume);
export const alignmentAgent = (resume: Resume, jd: string) => backendService.alignmentAgent(resume, jd);
export const interviewCoachAgent = (alignment: AlignmentReport, history: { role: 'user' | 'agent'; text: string }[]) => backendService.interviewCoachAgent(alignment, history);
