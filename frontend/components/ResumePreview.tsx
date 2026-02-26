
import React, { useState } from 'react';
import { Resume } from '../types';

interface ResumePreviewProps {
  resume: Resume | null;
}

export const ResumePreview: React.FC<ResumePreviewProps> = ({ resume }) => {
  const [activeTab, setActiveTab] = useState('basics');

  if (!resume) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-slate-400 p-8 text-center bg-white">
        <div className="w-16 h-16 bg-slate-50 border border-slate-100 rounded-2xl flex items-center justify-center mb-4">
          <svg className="w-8 h-8 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
        </div>
        <p className="font-semibold text-sm text-slate-600">Resume Preview Workspace</p>
        <p className="text-xs text-slate-400">Structured data will appear here after parsing.</p>
      </div>
    );
  }

  const tabs = [
    { id: 'basics', label: 'Summary' },
    { id: 'experience', label: 'Experience' },
    { id: 'education', label: 'Education' },
    { id: 'skills', label: 'Skills' },
    { id: 'projects', label: 'Projects' },
    { id: 'certifications', label: 'Certifications' },
    { id: 'awards', label: 'Awards' },
  ];

  return (
    <div className="bg-white h-full flex flex-col animate-in fade-in duration-500">
      <div className="p-8 border-b border-slate-100 sticky top-0 bg-white/90 backdrop-blur-md z-10">
        <div className="flex justify-between items-start mb-8">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900">{resume.name}</h2>
            <div className="flex gap-4 mt-2 text-xs font-medium text-slate-400">
              <span className="flex items-center gap-1.5"><svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>{resume.email}</span>
              {resume.phone && <span className="flex items-center gap-1.5"><svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"></path></svg>{resume.phone}</span>}
            </div>
          </div>
          <button className="text-[11px] font-bold text-slate-500 border border-slate-200 px-4 py-2 rounded-lg hover:bg-slate-50 transition-all flex items-center gap-2 shadow-sm">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0L8 8m4-4v12"></path></svg>
            Export
          </button>
        </div>

        <div className="inline-flex h-9 items-center justify-center rounded-lg bg-slate-100 p-1 text-slate-500">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`inline-flex items-center justify-center whitespace-nowrap rounded-md px-4 py-1.5 text-[11px] font-medium transition-all focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50 ${
                activeTab === tab.id 
                  ? 'bg-white text-slate-950 shadow-sm' 
                  : 'hover:text-slate-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-10 max-w-4xl mx-auto w-full">
        {activeTab === 'basics' && (
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
             <h3 className="text-xs font-bold text-slate-400 uppercase tracking-[0.2em] mb-6">Profile Narrative</h3>
             <div className="p-8 bg-slate-50 border border-slate-200 rounded-2xl relative">
                <div className="absolute top-4 left-4 text-slate-200">
                  <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 24 24"><path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10h-9.983zm-14.017 0v-7.391c0-5.704 3.748-9.57 9-10.609l.996 2.154c-2.433.917-3.996 3.638-3.996 5.849h3.983v10h-9.983z" /></svg>
                </div>
                <p className="text-slate-700 leading-relaxed text-sm relative z-10 font-medium">
                  {resume.summary || "No professional summary provided."}
                </p>
             </div>
          </div>
        )}

        {activeTab === 'experience' && (
          <div className="space-y-10 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {resume.experience.map((exp, idx) => (
              <div key={idx} className="group">
                <div className="flex justify-between items-baseline mb-3">
                  <h4 className="text-base font-bold text-slate-900">{exp.role}</h4>
                  <span className="text-[10px] font-bold bg-slate-100 text-slate-500 px-2 py-1 rounded border border-slate-200">{exp.duration}</span>
                </div>
                <p className="text-xs font-semibold text-slate-500 mb-4">{exp.company}</p>
                <ul className="space-y-2.5">
                  {exp.achievements.map((ach, aidx) => (
                    <li key={aidx} className="text-[13px] text-slate-600 flex gap-3 leading-relaxed">
                      <span className="text-slate-300 font-bold shrink-0">•</span>
                      {ach}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'education' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {resume.education.map((edu, idx) => (
              <div key={idx} className="p-6 bg-white border border-slate-200 rounded-xl hover:shadow-md transition-shadow">
                <h4 className="font-bold text-slate-900 mb-1.5 text-sm">{edu.degree}</h4>
                <p className="text-xs font-semibold text-slate-500 mb-4">{edu.institution}</p>
                <div className="flex items-center gap-2">
                   <div className="px-2 py-0.5 bg-slate-50 text-[10px] text-slate-400 border border-slate-100 rounded font-bold uppercase">{edu.year}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'skills' && (
          <div className="flex flex-wrap gap-2 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {resume.skills.map((skill, idx) => (
              <span key={idx} className="bg-white border border-slate-200 text-slate-700 px-3.5 py-1.5 rounded-lg text-[11px] font-semibold hover:border-slate-400 transition-colors shadow-sm">
                {skill}
              </span>
            ))}
          </div>
        )}

        {activeTab === 'projects' && (
          <div className="grid grid-cols-1 gap-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {resume.projects && resume.projects.length > 0 ? resume.projects.map((proj, idx) => (
              <div key={idx} className="p-6 bg-slate-50/50 border border-slate-200 rounded-xl">
                <div className="flex justify-between items-center mb-4">
                  <h4 className="font-bold text-sm text-slate-900">{proj.title}</h4>
                  <span className="text-[10px] font-bold text-slate-400">{proj.date}</span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">{proj.description}</p>
              </div>
            )) : <div className="text-center py-12 text-slate-300 italic text-xs border-2 border-dashed border-slate-100 rounded-xl">No projects found.</div>}
          </div>
        )}

        {activeTab === 'certifications' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
             {resume.certifications && resume.certifications.length > 0 ? resume.certifications.map((cert, idx) => (
               <div key={idx} className="flex items-start gap-4 p-5 bg-white border border-slate-200 rounded-xl">
                  <div className="p-2.5 bg-slate-50 border border-slate-100 rounded-lg text-lg">📜</div>
                  <div>
                    <h4 className="text-[13px] font-bold text-slate-900 mb-0.5">{cert.name}</h4>
                    <p className="text-[10px] text-slate-400 font-bold uppercase">{cert.issuer}</p>
                    <p className="text-[10px] text-slate-300 font-medium mt-1">{cert.date}</p>
                  </div>
               </div>
             )) : <div className="col-span-2 text-center py-12 text-slate-300 italic text-xs border-2 border-dashed border-slate-100 rounded-xl">No certifications found.</div>}
          </div>
        )}

        {activeTab === 'awards' && (
          <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
             {resume.awards && resume.awards.length > 0 ? resume.awards.map((award, idx) => (
               <div key={idx} className="flex gap-4 p-6 bg-white border border-slate-200 rounded-xl">
                  <div className="p-3 bg-slate-50 border border-slate-100 rounded-lg text-xl">🏆</div>
                  <div>
                    <h4 className="text-[13px] font-bold text-slate-900 mb-0.5">{award.title}</h4>
                    <p className="text-[10px] text-slate-400 font-bold uppercase">{award.issuer}</p>
                    <div className="inline-block mt-3 px-2 py-0.5 bg-slate-100 text-[9px] font-black text-slate-500 rounded uppercase tracking-tighter">{award.date}</div>
                  </div>
               </div>
             )) : <div className="text-center py-12 text-slate-300 italic text-xs border-2 border-dashed border-slate-100 rounded-xl">No awards found.</div>}
          </div>
        )}
      </div>
    </div>
  );
};
