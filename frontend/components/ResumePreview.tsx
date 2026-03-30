import React, { useMemo, useState } from "react";
import { Resume } from "../types";

interface ResumePreviewProps {
  resume: Resume | null;
}

const formatRange = (start?: string, end?: string): string => {
  if (start && end) return `${start} - ${end}`;
  if (start) return start;
  if (end) return end;
  return "";
};

export const ResumePreview: React.FC<ResumePreviewProps> = ({ resume }) => {
  const [activeTab, setActiveTab] = useState("work");

  const tabs = useMemo(
    () => [
      { id: "work", label: "Work" },
      { id: "education", label: "Education" },
      { id: "skills", label: "Skills" },
      { id: "projects", label: "Projects" },
      { id: "certificates", label: "Certificates" },
      { id: "awards", label: "Awards" },
    ],
    []
  );

  if (!resume) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-slate-400 p-8 text-center bg-white">
        <div className="w-16 h-16 bg-slate-50 border border-slate-100 rounded-2xl flex items-center justify-center mb-4">
          <svg
            className="w-8 h-8 opacity-20"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            ></path>
          </svg>
        </div>
        <p className="font-semibold text-sm text-slate-600">
          Resume Preview Workspace
        </p>
        <p className="text-xs text-slate-400">
          Structured data will appear here after parsing.
        </p>
      </div>
    );
  }

  const workItems = resume.work ?? [];
  const educationItems = resume.education ?? [];
  const skillItems = resume.skills ?? [];
  const projectItems = resume.projects ?? [];
  const certificateItems = resume.certificates ?? [];
  const awardItems = resume.awards ?? [];

  return (
    <div className="bg-white h-full flex flex-col animate-in fade-in duration-500">
      <div className="p-8 border-b border-slate-100 sticky top-0 bg-white/90 backdrop-blur-md z-10">
        <div className="flex justify-between items-start mb-8">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900">
              Resume Preview
            </h2>
            <div className="flex gap-4 mt-2 text-xs font-medium text-slate-400">
              <span>JSON Resume</span>
            </div>
          </div>
          <button className="text-[11px] font-bold text-slate-500 border border-slate-200 px-4 py-2 rounded-lg hover:bg-slate-50 transition-all flex items-center gap-2 shadow-sm">
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0L8 8m4-4v12"></path>
            </svg>
            Export
          </button>
        </div>

        <div className="inline-flex h-9 items-center justify-center rounded-lg bg-slate-100 p-1 text-slate-500 flex-wrap">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`inline-flex items-center justify-center whitespace-nowrap rounded-md px-4 py-1.5 text-[11px] font-medium transition-all focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50 ${
                activeTab === tab.id
                  ? "bg-white text-slate-950 shadow-sm"
                  : "hover:text-slate-900"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-10 max-w-4xl mx-auto w-full">
        {activeTab === "work" && (
          <div className="space-y-10 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {workItems.length > 0 ? (
              workItems.map((item, index) => (
                <div key={`${item.name}-${item.position}-${index}`} className="group">
                  <div className="flex justify-between items-baseline mb-3">
                    <h4 className="text-base font-bold text-slate-900">
                      {item.position || "Role"}
                    </h4>
                    <span className="text-[10px] font-bold bg-slate-100 text-slate-500 px-2 py-1 rounded border border-slate-200">
                      {formatRange(item.startDate, item.endDate) || "Dates"}
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-slate-500 mb-4">
                    {item.name || "Company"}
                  </p>
                  {item.summary && (
                    <p className="text-[13px] text-slate-600 leading-relaxed mb-4">
                      {item.summary}
                    </p>
                  )}
                  {item.highlights && item.highlights.length > 0 && (
                    <ul className="space-y-2.5">
                      {item.highlights.map((highlight, idx) => (
                        <li
                          key={`${highlight}-${idx}`}
                          className="text-[13px] text-slate-600 flex gap-3 leading-relaxed"
                        >
                          <span className="text-slate-300 font-bold shrink-0">-</span>
                          {highlight}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))
            ) : (
              <div className="text-center py-12 text-slate-300 italic text-xs border-2 border-dashed border-slate-100 rounded-xl">
                No work history found.
              </div>
            )}
          </div>
        )}

        {activeTab === "education" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {educationItems.length > 0 ? (
              educationItems.map((edu, index) => (
                <div
                  key={`${edu.institution}-${edu.area}-${index}`}
                  className="p-6 bg-white border border-slate-200 rounded-xl hover:shadow-md transition-shadow"
                >
                  <h4 className="font-bold text-slate-900 mb-1.5 text-sm">
                    {[edu.studyType, edu.area].filter(Boolean).join(" ") || "Education"}
                  </h4>
                  <p className="text-xs font-semibold text-slate-500 mb-3">
                    {edu.institution || "Institution"}
                  </p>
                  <div className="flex items-center gap-2 flex-wrap">
                    {formatRange(edu.startDate, edu.endDate) && (
                      <div className="px-2 py-0.5 bg-slate-50 text-[10px] text-slate-400 border border-slate-100 rounded font-bold uppercase">
                        {formatRange(edu.startDate, edu.endDate)}
                      </div>
                    )}
                    {edu.score && (
                      <div className="px-2 py-0.5 bg-slate-50 text-[10px] text-slate-400 border border-slate-100 rounded font-bold uppercase">
                        Score {edu.score}
                      </div>
                    )}
                  </div>
                  {edu.courses && edu.courses.length > 0 && (
                    <div className="mt-4 text-[11px] text-slate-500">
                      Courses: {edu.courses.join(", ")}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="col-span-2 text-center py-12 text-slate-300 italic text-xs border-2 border-dashed border-slate-100 rounded-xl">
                No education entries found.
              </div>
            )}
          </div>
        )}

        {activeTab === "skills" && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {skillItems.length > 0 ? (
              skillItems.map((skill, index) => (
                <div
                  key={`${skill.name}-${index}`}
                  className="p-4 bg-white border border-slate-200 rounded-xl"
                >
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-bold text-slate-900">
                      {skill.name || "Skill"}
                    </h4>
                    {skill.level && (
                      <span className="text-[10px] font-bold text-slate-400 uppercase">
                        {skill.level}
                      </span>
                    )}
                  </div>
                  {skill.keywords && skill.keywords.length > 0 && (
                    <div className="text-[11px] text-slate-500">
                      {skill.keywords.join(", ")}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-center py-12 text-slate-300 italic text-xs border-2 border-dashed border-slate-100 rounded-xl col-span-2">
                No skills found.
              </div>
            )}
          </div>
        )}

        {activeTab === "projects" && (
          <div className="grid grid-cols-1 gap-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {projectItems.length > 0 ? (
              projectItems.map((proj, index) => (
                <div
                  key={`${proj.name}-${index}`}
                  className="p-6 bg-slate-50/50 border border-slate-200 rounded-xl"
                >
                  <div className="flex justify-between items-center mb-4">
                    <h4 className="font-bold text-sm text-slate-900">
                      {proj.name || "Project"}
                    </h4>
                    <span className="text-[10px] font-bold text-slate-400">
                      {formatRange(proj.startDate, proj.endDate)}
                    </span>
                  </div>
                  {proj.description && (
                    <p className="text-xs text-slate-600 leading-relaxed mb-3">
                      {proj.description}
                    </p>
                  )}
                  {proj.highlights && proj.highlights.length > 0 && (
                    <ul className="space-y-2">
                      {proj.highlights.map((highlight, idx) => (
                        <li
                          key={`${highlight}-${idx}`}
                          className="text-[12px] text-slate-600 flex gap-3 leading-relaxed"
                        >
                          <span className="text-slate-300 font-bold shrink-0">-</span>
                          {highlight}
                        </li>
                      ))}
                    </ul>
                  )}
                  {proj.url && (
                    <div className="mt-3 text-[11px] text-slate-400 break-all">
                      {proj.url}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-center py-12 text-slate-300 italic text-xs border-2 border-dashed border-slate-100 rounded-xl">
                No projects found.
              </div>
            )}
          </div>
        )}

        {activeTab === "certificates" && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {certificateItems.length > 0 ? (
              certificateItems.map((cert, index) => (
                <div
                  key={`${cert.issuer}-${cert.name}-${index}`}
                  className="flex items-start gap-4 p-5 bg-white border border-slate-200 rounded-xl"
                >
                  <div className="p-2.5 bg-slate-50 border border-slate-100 rounded-lg text-[11px] font-bold text-slate-500">
                    CERT
                  </div>
                  <div>
                    <h4 className="text-[13px] font-bold text-slate-900 mb-0.5">
                      {cert.name || "Certificate"}
                    </h4>
                    <p className="text-[10px] text-slate-400 font-bold uppercase">
                      {cert.issuer || "Issuer"}
                    </p>
                    {cert.date && (
                      <p className="text-[10px] text-slate-300 font-medium mt-1">
                        {cert.date}
                      </p>
                    )}
                    {cert.url && (
                      <p className="text-[10px] text-slate-300 font-medium mt-1 break-all">
                        {cert.url}
                      </p>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="col-span-2 text-center py-12 text-slate-300 italic text-xs border-2 border-dashed border-slate-100 rounded-xl">
                No certificates found.
              </div>
            )}
          </div>
        )}

        {activeTab === "awards" && (
          <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {awardItems.length > 0 ? (
              awardItems.map((award, index) => (
                <div
                  key={`${award.awarder}-${award.title}-${index}`}
                  className="flex gap-4 p-6 bg-white border border-slate-200 rounded-xl"
                >
                  <div className="p-3 bg-slate-50 border border-slate-100 rounded-lg text-[11px] font-bold text-slate-500">
                    AWARD
                  </div>
                  <div>
                    <h4 className="text-[13px] font-bold text-slate-900 mb-0.5">
                      {award.title || "Award"}
                    </h4>
                    <p className="text-[10px] text-slate-400 font-bold uppercase">
                      {award.awarder || "Issuer"}
                    </p>
                    {award.date && (
                      <div className="inline-block mt-3 px-2 py-0.5 bg-slate-100 text-[9px] font-black text-slate-500 rounded uppercase tracking-tighter">
                        {award.date}
                      </div>
                    )}
                    {award.summary && (
                      <p className="text-[11px] text-slate-500 mt-3">
                        {award.summary}
                      </p>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-12 text-slate-300 italic text-xs border-2 border-dashed border-slate-100 rounded-xl">
                No awards found.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
