import { 
  Resume, 
  ResumeCriticReport, 
  ContentStrengthReport, 
  AlignmentReport,
  ChatRequest,
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
  metadata?: {
    needs_review?: boolean;
    checkpoint_id?: string;
    review_payload?: any;
    review_required?: boolean;
  };
  decision_trace?: string[];
  sharp_metadata?: Record<string, any>;
}

interface InterviewCoachPayload {
  current_question_number?: number;
  total_questions?: number;
  interview_type?: string;
  question?: string;
  keywords?: string[];
  tip?: string;
  feedback?: string;
  answer_score?: number;
  can_proceed?: boolean;
  next_challenge?: string;
  interview_complete?: boolean;
  summary?: string;
  strengths?: string[];
  areas_for_improvement?: string[];
  overall_rating?: string;
  recommendations?: string[];
  final_feedback?: string;
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const asStringArray = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];

const parseInterviewCoachPayload = (payload: unknown): InterviewCoachPayload | null => {
  if (typeof payload === 'string') {
    try {
      const parsed = JSON.parse(payload);
      return isRecord(parsed) ? parsed as InterviewCoachPayload : null;
    } catch {
      return null;
    }
  }

  return isRecord(payload) ? payload as InterviewCoachPayload : null;
};

export const formatInterviewCoachPayload = (payload: unknown): string => {
  const parsed = parseInterviewCoachPayload(payload);
  if (!parsed) {
    return typeof payload === 'string' ? payload : "I'm sorry, I couldn't generate a response.";
  }

  if (parsed.interview_complete) {
    const lines = [
      'Interview complete.',
      parsed.overall_rating ? `Overall rating: ${parsed.overall_rating}` : '',
      parsed.summary || '',
      parsed.strengths?.length ? `Strengths: ${parsed.strengths.join(', ')}` : '',
      parsed.areas_for_improvement?.length
        ? `Areas to improve: ${parsed.areas_for_improvement.join(', ')}`
        : '',
      parsed.recommendations?.length
        ? `Recommendations: ${parsed.recommendations.join(', ')}`
        : '',
      parsed.final_feedback || '',
    ];

    return lines.filter(Boolean).join('\n\n');
  }

  const questionLabel =
    parsed.current_question_number && parsed.total_questions
      ? `Question ${parsed.current_question_number} of ${parsed.total_questions}`
      : 'Interview question';

  const lines = [
    questionLabel,
    parsed.question || '',
    parsed.feedback ? `Feedback: ${parsed.feedback}` : '',
    typeof parsed.answer_score === 'number' ? `Score: ${Math.round(parsed.answer_score)}/100` : '',
    parsed.tip ? `Tip: ${parsed.tip}` : '',
    parsed.next_challenge ? `Next focus: ${parsed.next_challenge}` : '',
  ];

  return lines.filter(Boolean).join('\n\n');
};

class BackendService {
  private sessionId: string = '';
  private initialized: boolean = false;

  async initialize(): Promise<void> {
    if (this.initialized) return;
    
    const response = await fetch(`${API_BASE_URL}/api/v1/sessions/new`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAuthToken()}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    this.sessionId = data.session_id;
    this.initialized = true;
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

  formatInterviewCoachPayload(payload: unknown): string {
    return formatInterviewCoachPayload(payload);
  }

  async callChatEndpoint(request: ChatRequest): Promise<ChatResponse> {
    // Safe base64 encoding for audio data to avoid stack overflow
    let audioDataBase64: string | null = null;
    if (request.audioData) {
      const bytes = new Uint8Array(request.audioData);
      let binary = '';
      for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
      }
      audioDataBase64 = btoa(binary);
    }

    const requestBody = {
      ...request,
      audioData: audioDataBase64,
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

  async resumeCriticAgent(resume: Resume): Promise<ResumeCriticReport> {
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

  async contentStrengthAgent(resume?: Resume | null): Promise<ContentStrengthReport> {
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
      let data: unknown = response.payload;
      if (!isRecord(data)) {
        data = JSON.parse(response.content || '{}');
      }
      const parsed = isRecord(data) ? data : {};
      return {
        skillsMatch: asStringArray(parsed.skillsMatch),
        missingSkills: asStringArray(parsed.missingSkills),
        experienceMatch: asStringArray(parsed.experienceMatch),
        summary: typeof parsed.summary === 'string' ? parsed.summary : ''
      };
    } catch (error) {
      console.error('Failed to parse alignment response:', error);
      throw new Error('Invalid response from alignment agent');
    }
  }

  async interviewCoachAgent(
    resume: Resume | null | undefined,
    jobDescription: string,
    history: { role: 'user' | 'agent'; text: string }[]
  ): Promise<string> {
    const request: ChatRequest = {
      intent: 'INTERVIEW_COACH',
      jobDescription,
      messageHistory: history
    };
    if (this.hasResumeContent(resume)) request.resumeData = resume;

    const response = await this.callChatEndpoint(request);
    return formatInterviewCoachPayload(response.payload ?? response.content);
  }
}

export const backendService = new BackendService();

// Export individual functions for backward compatibility
export const resumeCriticAgent = (resume: Resume) => backendService.resumeCriticAgent(resume);
export const contentStrengthAgent = (resume?: Resume | null) => backendService.contentStrengthAgent(resume);
export const alignmentAgent = (resume: Resume | null | undefined, jd: string) => backendService.alignmentAgent(resume, jd);
export const interviewCoachAgent = (
  resume: Resume | null | undefined,
  jobDescription: string,
  history: { role: 'user' | 'agent'; text: string }[]
) => backendService.interviewCoachAgent(resume, jobDescription, history);
