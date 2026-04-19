import React from 'react';
import { ResumeCriticReport, ResumeSchema } from '../../types';
import { resolveResumeLocation } from '@/utils/resolve-resume-location';
import { capitalizeFirst } from '@/utils/text';
import { ReportHeader } from '../ReportHeader';

export const CriticStep: React.FC<{
  report: ResumeCriticReport;
  resume?: ResumeSchema | null;
  onApprove: () => void;
}> = ({ report, resume, onApprove }) => {
  const issues = Array.isArray(report.issues) ? report.issues : [];
  const score =
    typeof report.score === "number" ? Math.round(report.score) : null;
  const summary =
    typeof report.summary === "string" && report.summary.trim()
      ? report.summary
      : "Resume processed successfully.";
  const severityClass = (severity: string) => {
    if (severity === "HIGH") return "bg-red-50 text-red-700 border-red-200";
    if (severity === "MEDIUM")
      return "bg-amber-50 text-amber-700 border-amber-200";
    return "bg-slate-100 text-slate-600 border-slate-200";
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-400 space-y-6">
      <ReportHeader title="Resume Critique" summary={summary} score={score} />

      <div className="space-y-3">
        <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
          Issue List
        </h4>
        <div className="space-y-2">
          {issues.length === 0 && (
            <div className="p-3 bg-white border border-slate-200 rounded-lg text-xs text-slate-500">
              No critical issues detected. Proceed when ready.
            </div>
          )}
          {issues.map((issue, i) => (
            <div
              key={`issue-${issue.type}-${i}`}
              className="p-3 bg-white border border-slate-200 rounded-lg space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-900">
                  {issue.type?.toUpperCase?.() || "ISSUE"}
                </span>
                <span
                  className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded border ${severityClass(issue.severity)}`}
                >
                  {issue.severity}
                </span>
              </div>
              <p className="text-[12px] text-slate-600 leading-relaxed">
                {issue.description}
              </p>
              {(() => {
                const resolved = resolveResumeLocation(resume, issue.location);
                return (
                  <div className="space-y-1.5 text-[10px] text-slate-400">
                    <div>
                      Section:{" "}
                      <span className="font-medium text-slate-600">
                        {capitalizeFirst(resolved.topLevel || "unknown")}
                      </span>
                    </div>
                  </div>
                );
              })()}
            </div>
          ))}
        </div>
      </div>

      <button
        onClick={onApprove}
        className="w-full bg-slate-900 text-white text-[13px] font-semibold py-3 rounded-lg shadow-sm hover:bg-slate-800 active:scale-[0.98] transition-all"
      >
        Run Content Strength Analysis
      </button>
    </div>
  );
};
