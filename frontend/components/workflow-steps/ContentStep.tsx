import React from 'react';
import { ContentStrengthReport, ResumeSchema } from '../../types';
import { resolveResumeLocation } from '@/utils/resolve-resume-location';
import { capitalizeFirst } from '@/utils/text';
import { ReportHeader } from '../ReportHeader';

export const ContentStep: React.FC<{
  report: ContentStrengthReport;
  resume?: ResumeSchema | null;
  onApprove: () => void;
}> = ({ report, resume, onApprove }) => {
  const suggestions = Array.isArray(report.suggestions)
    ? report.suggestions
    : [];
  const score =
    typeof report.score === "number" ? Math.round(report.score) : null;
  const summary =
    typeof report.summary === "string" && report.summary.trim()
      ? report.summary
      : "Content analysis complete.";
  const evidenceClass = (level: string) => {
    if (level === "HIGH")
      return "bg-emerald-50 text-emerald-700 border-emerald-200";
    if (level === "MEDIUM")
      return "bg-amber-50 text-amber-700 border-amber-200";
    return "bg-slate-100 text-slate-600 border-slate-200";
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-400 space-y-8">
      <ReportHeader title="Content Strength" summary={summary} score={score} />

      <div className="space-y-3">
        <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
          Revision Suggestions
        </h4>
        <div className="space-y-3">
          {suggestions.length === 0 && (
            <div className="p-3 bg-white border border-slate-200 rounded-lg text-xs text-slate-500">
              No suggestions returned. Proceed when ready.
            </div>
          )}
          {suggestions.map((sug, i) => (
            <div
              key={`suggestion-${sug.type}-${i}`}
              className="p-4 bg-white border border-slate-200 rounded-xl space-y-3"
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-900">
                  {sug.type?.replace?.("_", " ")?.toUpperCase?.() ||
                    "SUGGESTION"}
                </span>
                <span
                  className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded border ${evidenceClass(sug.evidenceStrength)}`}
                >
                  {sug.evidenceStrength}
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-[9px] font-bold text-slate-500 uppercase mb-1">
                    Original
                  </p>
                  <p className="text-[11px] text-slate-500 line-through">
                    {sug.original}
                  </p>
                </div>
                <div>
                  <p className="text-[9px] font-bold text-emerald-600 uppercase mb-1">
                    Suggested
                  </p>
                  <p className="text-[11px] text-slate-900 font-medium">
                    {sug.suggested}
                  </p>
                </div>
              </div>
              {(() => {
                const resolved = resolveResumeLocation(resume, sug.location);
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
        className="w-full bg-slate-900 text-white text-[13px] font-semibold py-3 rounded-lg shadow-sm hover:bg-slate-800 transition-all"
      >
        Proceed to Job Alignment
      </button>
    </div>
  );
};
