import React from 'react';
import { AlignmentReport, ResumeSchema } from '../../types';
import { resolveResumeLocation } from '@/utils/resolve-resume-location';

export const AlignmentReportStep: React.FC<{
  report: AlignmentReport;
  resume?: ResumeSchema | null;
  onStartInterview: () => void;
}> = ({ report, resume, onStartInterview }) => {
  const resolveEvidence = (paths: string[]) =>
    paths
      .map((path) => {
        const resolved = resolveResumeLocation(resume, path);
        return resolved.isValid && resolved.display ? resolved.display : "";
      })
      .filter(
        (value): value is string =>
          typeof value === "string" && value.trim().length > 0,
      );

  const matchedSkills = resolveEvidence(report.skillsMatch);
  const experienceEvidence = resolveEvidence(report.experienceMatch);
  const missingSkills = Array.isArray(report.missingSkills)
    ? report.missingSkills
    : [];

  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-400 space-y-6">
      <div className="flex items-start justify-between border-b border-slate-100 pb-4">
        <div>
          <h3 className="text-lg font-semibold">Job Alignment Report</h3>
          <p className="text-[11px] text-slate-500">
            Match based on resume and job description.
          </p>
        </div>
      </div>

      <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
          Summary
        </p>
        <p className="text-xs text-slate-700 leading-relaxed font-medium">
          {report.summary || "No summary provided yet."}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3">
        <div className="p-3.5 bg-white border border-slate-200 rounded-xl">
          <p className="text-[9px] font-bold text-slate-400 uppercase mb-2 tracking-widest">
            Matched Skills
          </p>
          <div className="flex flex-wrap gap-1">
            {matchedSkills.length > 0 ? (
              matchedSkills.slice(0, 8).map((k, i) => (
                <span
                  key={`matched-skill-${k}-${i}`}
                  className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200 font-medium"
                >
                  {k}
                </span>
              ))
            ) : (
              <span className="text-[10px] text-slate-400">
                No matched skill was identified.
              </span>
            )}
          </div>
        </div>
        <div className="p-3.5 bg-white border border-slate-200 rounded-xl">
          <p className="text-[9px] font-bold text-slate-400 uppercase mb-2 tracking-widest">
            Missing Skills
          </p>
          <div className="flex flex-wrap gap-1">
            {missingSkills.length > 0 ? (
              missingSkills.slice(0, 8).map((k, i) => (
                <span
                  key={`missing-skill-${k}-${i}`}
                  className="text-[10px] bg-red-50 text-red-600 px-2 py-0.5 rounded border border-red-100 font-medium"
                >
                  {k}
                </span>
              ))
            ) : (
              <span className="text-[10px] text-slate-400">
                No missing skill was identified.
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="p-3.5 bg-white border border-slate-200 rounded-xl">
        <p className="text-[9px] font-bold text-slate-400 uppercase mb-2 tracking-widest">
          Experience Evidence
        </p>
        <div className="flex flex-wrap gap-1">
          {experienceEvidence.length > 0 ? (
            experienceEvidence.slice(0, 8).map((item, i) => (
              <span
                key={`experience-evidence-${item}-${i}`}
                className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200 font-medium"
              >
                {item}
              </span>
            ))
          ) : (
            <span className="text-[10px] text-slate-400">
              No experience evidence was identified.
            </span>
          )}
        </div>
      </div>

      <button
        onClick={onStartInterview}
        className="w-full bg-slate-900 text-white text-[13px] font-semibold py-3 rounded-lg shadow-sm hover:bg-slate-800 transition-all"
      >
        Launch Mock Interview
      </button>
    </div>
  );
};
