import { z } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';

export interface Work {
  name?: string;
  position?: string;
  url?: string;
  startDate?: string;
  endDate?: string;
  highlights?: string[];
}

export interface Education {
  institution?: string;
  url?: string;
  area?: string;
  studyType?: string;
  startDate?: string;
  endDate?: string;
  score?: string;
  courses?: string[];
}

export interface Award {
  title?: string;
  date?: string;
  awarder?: string;
  summary?: string;
}

export interface Certificate {
  name?: string;
  date?: string;
  issuer?: string;
  url?: string;
}

export interface Skill {
  name?: string;
}

export interface Project {
  name?: string;
  startDate?: string;
  endDate?: string;
  description?: string;
  highlights?: string[];
  url?: string;
}

export interface ResumeSchema {
  work?: Work[];
  education?: Education[];
  awards?: Award[];
  certificates?: Certificate[];
  skills?: Skill[];
  projects?: Project[];
}

// Backward compatibility alias
export type Resume = ResumeSchema;

export type EvidenceStrength = "HIGH" | "MEDIUM" | "LOW";
export type ResumeCriticIssueType = "ats" | "structure" | "impact" | "readability";
export type ResumeCriticSeverity = "HIGH" | "MEDIUM" | "LOW";
export type ContentSuggestionType = "action_verb" | "specificity" | "structure" | "redundancy";

export interface ResumeCriticIssue {
  location: string;
  type: ResumeCriticIssueType;
  severity: ResumeCriticSeverity;
  description: string;
}

export interface ResumeCriticReport {
  issues: ResumeCriticIssue[];
  summary: string;
  score?: number;
}

export interface ContentSuggestion {
  location: string;
  original: string;
  suggested: string;
  evidenceStrength: EvidenceStrength;
  type: ContentSuggestionType;
}

export interface ContentStrengthReport {
  suggestions: ContentSuggestion[];
  summary: string;
  score?: number;
}

export interface AlignmentReport {
  skillsMatch: string[];
  missingSkills: string[];
  experienceMatch: string;
  fitScore: number;
  reasoning: string;
  sources?: { title: string; uri: string }[];
}

export enum WorkflowStatus {
  IDLE = 'IDLE',
  EXTRACTING = 'EXTRACTING',
  ROUTING = 'ROUTING',
  CRITIQUING = 'CRITIQUING',
  AWAITING_CRITIC_APPROVAL = 'AWAITING_CRITIC_APPROVAL',
  ANALYZING_CONTENT = 'ANALYZING_CONTENT',
  AWAITING_CONTENT_APPROVAL = 'AWAITING_CONTENT_APPROVAL',
  ALIGNING_JD = 'ALIGNING_JD',
  AWAITING_ALIGNMENT_APPROVAL = 'AWAITING_ALIGNMENT_APPROVAL',
  INTERVIEWING = 'INTERVIEWING',
  SELECTING_INTERVIEW_MODE = 'SELECTING_INTERVIEW_MODE',
  DEBUG_VOICE = 'DEBUG_VOICE',
  COMPLETED = 'COMPLETED'
}

export type InterviewMode = 'CHAT' | 'VOICE';

export interface ResumeFile {
  data: string;
  fileType: 'pdf';
}

export interface ChatRequest {
  intent: 'RESUME_CRITIC' | 'CONTENT_STRENGTH' | 'ALIGNMENT' | 'INTERVIEW_COACH';
  resumeData?: ResumeSchema | null;
  jobDescription: string;
  messageHistory: InterviewMessage[];
  resumeFile?: ResumeFile;
  audioData?: Uint8Array | null;
}

export interface InterviewMessage {
  role: 'user' | 'agent';
  text: string;
}

export interface SharedState {
  currentResume: ResumeSchema | null;
  history: ResumeSchema[];
  jobDescription: string;
  status: WorkflowStatus;
  criticReport: ResumeCriticReport | null;
  contentReport: ContentStrengthReport | null;
  alignmentReport: AlignmentReport | null;
  interviewHistory: InterviewMessage[];
  interviewMode?: InterviewMode;
}

export type ResumeLookupResult = {
  isValid: boolean;
  display?: string;
  topLevel?: string;
  usedSectionAsEvidence?: boolean;
};