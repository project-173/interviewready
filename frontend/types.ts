import { z } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';

export interface Work {
  name?: string;
  position?: string;
  url?: string;
  startDate?: string;
  endDate?: string;
  summary?: string;
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
  level?: string;
  keywords?: string[];
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

export interface StructuralAssessment {
  score: number;
  readability: string;
  formattingRecommendations: string[];
  suggestions: string[];
}

export type SkillCategory = "Technical" | "Soft" | "Domain" | "Tool";
export type EvidenceStrength = "HIGH" | "MEDIUM" | "LOW";
export type ImpactLevel = "HIGH" | "MEDIUM" | "LOW";

export interface ContentSkill {
  name: string;
  category: SkillCategory;
  confidenceScore: number;
  evidenceStrength: EvidenceStrength;
  evidence: string;
}

export interface ContentAchievement {
  description: string;
  impact: ImpactLevel;
  quantifiable: boolean;
  confidenceScore: number;
  originalText: string;
}

export interface ContentSuggestion {
  original: string;
  suggested: string;
  rationale: string;
  faithful: boolean;
  confidenceScore: number;
}

export interface ContentAnalysisReport {
  skills: ContentSkill[];
  achievements: ContentAchievement[];
  suggestions: ContentSuggestion[];
  hallucinationRisk: number;
  summary: string;
}

export interface AlignmentReport {
  skillsMatch: string[];
  missingSkills: string[];
  experienceMatch: string;
  fitScore: number;
  reasoning: string;
  sources?: { title: string; uri: string }[];
}

const workSchema = z.object({
  name: z.string(),
  position: z.string(),
  url: z.string(),
  startDate: z.string(),
  endDate: z.string(),
  summary: z.string(),
  highlights: z.array(z.string()),
}).partial();

const volunteerSchema = z.object({
  organization: z.string(),
  position: z.string(),
  url: z.string(),
  startDate: z.string(),
  endDate: z.string(),
  summary: z.string(),
  highlights: z.array(z.string()),
}).partial();

const educationSchema = z.object({
  institution: z.string(),
  url: z.string(),
  area: z.string(),
  studyType: z.string(),
  startDate: z.string(),
  endDate: z.string(),
  score: z.string(),
  courses: z.array(z.string()),
}).partial();

const awardSchema = z.object({
  title: z.string(),
  date: z.string(),
  awarder: z.string(),
  summary: z.string(),
}).partial();

const certificateSchema = z.object({
  name: z.string(),
  date: z.string(),
  issuer: z.string(),
  url: z.string(),
}).partial();

const publicationSchema = z.object({
  name: z.string(),
  publisher: z.string(),
  releaseDate: z.string(),
  url: z.string(),
  summary: z.string(),
}).partial();

const skillSchema = z.object({
  name: z.string(),
  level: z.string(),
  keywords: z.array(z.string()),
}).partial();

const languageSchema = z.object({
  language: z.string(),
  fluency: z.string(),
}).partial();

const interestSchema = z.object({
  name: z.string(),
  keywords: z.array(z.string()),
}).partial();

const referenceSchema = z.object({
  name: z.string(),
  reference: z.string(),
}).partial();

const projectSchema = z.object({
  name: z.string(),
  startDate: z.string(),
  endDate: z.string(),
  description: z.string(),
  highlights: z.array(z.string()),
  url: z.string(),
}).partial();

export const resumeJsonSchema = zodToJsonSchema(z.object({
  work: z.array(workSchema).optional(),
  volunteer: z.array(volunteerSchema).optional(),
  education: z.array(educationSchema).optional(),
  awards: z.array(awardSchema).optional(),
  certificates: z.array(certificateSchema).optional(),
  publications: z.array(publicationSchema).optional(),
  skills: z.array(skillSchema).optional(),
  languages: z.array(languageSchema).optional(),
  interests: z.array(interestSchema).optional(),
  references: z.array(referenceSchema).optional(),
  projects: z.array(projectSchema).optional(),
}), 'resumeSchema');

export const structuralAssessmentJsonSchema = zodToJsonSchema(z.object({
  score: z.number(),
  readability: z.string(),
  formattingRecommendations: z.array(z.string()),
  suggestions: z.array(z.string()),
}), 'structuralAssessmentSchema');

export const contentAnalysisReportJsonSchema = zodToJsonSchema(z.object({
  skills: z.array(z.object({
    name: z.string(),
    category: z.enum(["Technical", "Soft", "Domain", "Tool"]),
    confidenceScore: z.number(),
    evidenceStrength: z.enum(["HIGH", "MEDIUM", "LOW"]),
    evidence: z.string(),
  })),
  achievements: z.array(z.object({
    description: z.string(),
    impact: z.enum(["HIGH", "MEDIUM", "LOW"]),
    quantifiable: z.boolean(),
    confidenceScore: z.number(),
    originalText: z.string(),
  })),
  suggestions: z.array(z.object({
    original: z.string(),
    suggested: z.string(),
    rationale: z.string(),
    faithful: z.boolean(),
    confidenceScore: z.number(),
  })),
  hallucinationRisk: z.number(),
  summary: z.string(),
}), 'contentAnalysisReportSchema');

export const alignmentReportJsonSchema = zodToJsonSchema(z.object({
  skillsMatch: z.array(z.string()),
  missingSkills: z.array(z.string()),
  experienceMatch: z.string(),
  fitScore: z.number(),
  reasoning: z.string(),
  sources: z.array(z.object({
    title: z.string(),
    uri: z.string(),
  })).optional(),
}), 'alignmentReportSchema');

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
  COMPLETED = 'COMPLETED'
}

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
  criticReport: StructuralAssessment | null;
  contentReport: ContentAnalysisReport | null;
  alignmentReport: AlignmentReport | null;
  interviewHistory: InterviewMessage[];
}
