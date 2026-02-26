import { z } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';

export interface Experience {
  title: string;
  company: string;
  startDate: Date;
  endDate: Date | null;
  description: string;
}

export interface Education {
  school: string;
  degree: string;
  startDate: Date;
  endDate: Date | null;
  gpa: number | null;
  gpaMax: number | null;
  description: string;
}

export interface Project {
  title: string;
  startDate: Date;
  endDate: Date | null;
  description: Record<string, unknown> | null;
}

export interface Certification {
  name: string;
  issuer: string;
  issueDate: Date;
  expiryDate: Date | null;
  credentialId: string;
  credentialUrl: string;
}

export interface Award {
  title: string;
  issuer: string;
  date: Date | null;
  description: Record<string, unknown> | null;
}

export interface Contact {
  fullName: string;
  email: string;
  phone: string;
  city: string;
  country: string;
  linkedin: string;
  github: string;
  portfolio: string;
}

export interface Resume {
  title: string;
  summary: string;
  isMaster: boolean;
  experiences: Experience[];
  educations: Education[];
  skills: string[];
  awards: Award[];
  certifications: Certification[];
  projects: Project[];
  contact: Contact;
}

export interface StructuralAssessment {
  score: number;
  readability: string;
  formattingRecommendations: string[];
  suggestions: string[];
}

export interface ContentAnalysisReport {
  strengths: string[];
  gaps: string[];
  skillImprovements: string[];
  quantifiedImpactScore: number;
}

export interface AlignmentReport {
  overallScore: number;
  matchingKeywords: string[];
  missingKeywords: string[];
  roleFitAnalysis: string;
  sources?: { title: string; uri: string }[];
}

const experienceSchema = z.object({
  title: z.string(),
  company: z.string(),
  startDate: z.string(),
  endDate: z.string().nullable(),
  description: z.string(),
});

const educationSchema = z.object({
  school: z.string(),
  degree: z.string(),
  startDate: z.string(),
  endDate: z.string().nullable(),
  gpa: z.number().nullable(),
  gpaMax: z.number().nullable(),
  description: z.string(),
});

const projectSchema = z.object({
  title: z.string(),
  startDate: z.string(),
  endDate: z.string().nullable(),
  description: z.record(z.unknown()).nullable(),
});

const certificationSchema = z.object({
  name: z.string(),
  issuer: z.string(),
  issueDate: z.string(),
  expiryDate: z.string().nullable(),
  credentialId: z.string(),
  credentialUrl: z.string(),
});

const awardSchema = z.object({
  title: z.string(),
  issuer: z.string(),
  date: z.string().nullable(),
  description: z.record(z.unknown()).nullable(),
});

const contactSchema = z.object({
  fullName: z.string(),
  email: z.string(),
  phone: z.string(),
  city: z.string(),
  country: z.string(),
  linkedin: z.string(),
  github: z.string(),
  portfolio: z.string(),
});

export const resumeJsonSchema = zodToJsonSchema(z.object({
  title: z.string(),
  summary: z.string(),
  isMaster: z.boolean(),
  experiences: z.array(experienceSchema),
  educations: z.array(educationSchema),
  skills: z.array(z.string()),
  awards: z.array(awardSchema),
  certifications: z.array(certificationSchema),
  projects: z.array(projectSchema),
  contact: contactSchema,
}), 'resumeSchema');

export const structuralAssessmentJsonSchema = zodToJsonSchema(z.object({
  score: z.number(),
  readability: z.string(),
  formattingRecommendations: z.array(z.string()),
  suggestions: z.array(z.string()),
}), 'structuralAssessmentSchema');

export const contentAnalysisReportJsonSchema = zodToJsonSchema(z.object({
  strengths: z.array(z.string()),
  gaps: z.array(z.string()),
  skillImprovements: z.array(z.string()),
  quantifiedImpactScore: z.number(),
}), 'contentAnalysisReportSchema');

export const alignmentReportJsonSchema = zodToJsonSchema(z.object({
  overallScore: z.number(),
  matchingKeywords: z.array(z.string()),
  missingKeywords: z.array(z.string()),
  roleFitAnalysis: z.string(),
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

export interface SharedState {
  currentResume: Resume | null;
  history: Resume[];
  jobDescription: string;
  status: WorkflowStatus;
  criticReport: StructuralAssessment | null;
  contentReport: ContentAnalysisReport | null;
  alignmentReport: AlignmentReport | null;
  interviewHistory: { role: 'user' | 'agent'; text: string }[];
}
