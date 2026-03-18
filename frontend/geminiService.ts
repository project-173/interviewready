
import { GoogleGenAI } from "@google/genai";
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

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

export interface ExtractorFileData {
  data: string;
  mimeType: string;
}

export const extractorAgent = async (input: string | ExtractorFileData): Promise<Resume> => {
  const parts = [];
  
  if (typeof input === 'string') {
    parts.push({ text: `Parse the following resume text into a structured JSON format. Resume Text: ${input}` });
  } else {
    parts.push({
      inlineData: {
        mimeType: input.mimeType,
        data: input.data,
      },
    });
    parts.push({ text: "Parse the attached resume file into a structured JSON format." });
  }

  const response = await ai.models.generateContent({
    model: 'gemini-3-flash-preview',
    contents: { parts },
    config: {
      responseMimeType: "application/json",
      responseJsonSchema: resumeJsonSchema
    }
  });

  const data = JSON.parse(response.text || '{}');
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
};

export const resumeCriticAgent = async (resume: Resume): Promise<StructuralAssessment> => {
  const response = await ai.models.generateContent({
    model: 'gemini-3-flash-preview',
    contents: `Critique the structure and formatting of this resume: ${JSON.stringify(resume)}`,
    config: {
      responseMimeType: "application/json",
      responseJsonSchema: structuralAssessmentJsonSchema
    }
  });
  return JSON.parse(response.text || '{}');
};

export const contentStrengthAgent = async (resume: Resume): Promise<ContentAnalysisReport> => {
  const response = await ai.models.generateContent({
    model: 'gemini-3-flash-preview',
    contents: `Analyze the content strength and skills of this resume using STAR/XYZ methodology: ${JSON.stringify(resume)}`,
    config: {
      responseMimeType: "application/json",
      responseJsonSchema: contentAnalysisReportJsonSchema
    }
  });
  return JSON.parse(response.text || '{}');
};

export const alignmentAgent = async (resume: Resume, jd: string): Promise<AlignmentReport> => {
  const response = await ai.models.generateContent({
    model: 'gemini-3-flash-preview',
    contents: `Analyze the fit between this resume and the Job Description. Use Google Search to research the company or specific technology trends if necessary.
    Resume: ${JSON.stringify(resume)}
    JD: ${jd}`,
    config: {
      tools: [{ googleSearch: {} }],
    },
  });

  const sources = response.candidates?.[0]?.groundingMetadata?.groundingChunks
    ?.filter(chunk => chunk.web)
    ?.map(chunk => ({
      title: chunk.web?.title || 'Search Source',
      uri: chunk.web?.uri || ''
    })) || [];
  
  const responseStructured = await ai.models.generateContent({
    model: 'gemini-3-flash-preview',
    contents: `Based on your analysis of the fit between this resume and JD, provide a structured report.
    Resume: ${JSON.stringify(resume)}
    JD: ${jd}
    Detailed Analysis: ${response.text}`,
    config: {
      responseMimeType: "application/json",
      responseJsonSchema: alignmentReportJsonSchema
    }
  });
  
  const data = JSON.parse(responseStructured.text || '{}');
  return {
    ...data,
    sources
  };
};

export const interviewCoachAgent = async (
  alignment: AlignmentReport, 
  history: { role: 'user' | 'agent'; text: string }[]
): Promise<string> => {
  const response = await ai.models.generateContent({
    model: 'gemini-3-pro-preview',
    contents: `You are a high-stakes Interview Coach. Based on this alignment report: ${JSON.stringify(alignment)}, conduct a realistic mock interview. Ask one targeted question at a time. History: ${JSON.stringify(history)}`,
  });
  return response.text || "I'm sorry, I couldn't generate a response.";
};
