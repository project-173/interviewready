import { z } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';

export interface Experience {
  company: string;
  role: string;
  duration: string;
  achievements: string[];
}

export interface Education {
  institution: string;
  degree: string;
  year: string;
}

export interface Project {
  title: string;
  description: string;
  date: string;
}

export interface Certification {
  name: string;
  issuer: string;
  date: string;
}

export interface Award {
  title: string;
  issuer: string;
  date: string;
}

export interface ResumeSchema {
  skills?: string[];
  experiences?: Experience[];
  educations?: Education[];
  projects?: Project[];
  certifications?: Certification[];
  awards?: Award[];
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

const experienceSchema = z.object({
  company: z.string(),
  role: z.string(),
  duration: z.string(),
  achievements: z.array(z.string()),
});

const educationSchema = z.object({
  institution: z.string(),
  degree: z.string(),
  year: z.string(),
});

const projectSchema = z.object({
  title: z.string(),
  description: z.string(),
  date: z.string(),
});

const certificationSchema = z.object({
  name: z.string(),
  issuer: z.string(),
  date: z.string(),
});

const awardSchema = z.object({
  title: z.string(),
  issuer: z.string(),
  date: z.string(),
});

export const resumeJsonSchema = zodToJsonSchema(z.object({
  skills: z.array(z.string()),
  experiences: z.array(experienceSchema),
  educations: z.array(educationSchema),
  projects: z.array(projectSchema),
  certifications: z.array(certificationSchema),
  awards: z.array(awardSchema),
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
