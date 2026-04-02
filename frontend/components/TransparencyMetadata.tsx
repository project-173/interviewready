import React from 'react';
import { InterviewMessage } from '../types';

export const TransparencyMetadata: React.FC<{ message: InterviewMessage }> = ({
  message,
}) => {
  // Only show metadata for agent messages
  if (message.role !== 'agent') return null;

  const hasTransparencyData =
    message.confidence_score !== undefined ||
    message.reasoning ||
    message.decision_trace?.length ||
    message.improvement_suggestion ||
    message.bias_warnings?.length ||
    message.governance_flags?.length ||
    message.answer_score !== undefined ||
    message.can_proceed !== undefined;

  if (!hasTransparencyData) return null;

  return (
    <div className="mt-3 space-y-3 border-t border-slate-100 pt-3">
      {/* Confidence Score & Answer Evaluation */}
      {(message.confidence_score !== undefined || message.answer_score !== undefined) && (
        <div className="rounded-lg bg-gradient-to-r from-blue-50 to-indigo-50 p-3">
          <div className="text-[11px] font-semibold text-slate-600 uppercase tracking-widest">
            Confidence & Scoring
          </div>
          <div className="mt-2 space-y-1 text-[12px] text-slate-700">
            {message.confidence_score !== undefined && (
              <div className="flex items-center justify-between">
                <span>Model Confidence:</span>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-24 rounded-full bg-slate-200">
                    <div
                      className="h-2 rounded-full bg-blue-500"
                      style={{
                        width: `${Math.min(100, message.confidence_score * 100)}%`,
                      }}
                    />
                  </div>
                  <span className="font-semibold">
                    {Math.round(message.confidence_score * 100)}%
                  </span>
                </div>
              </div>
            )}
            {message.answer_score !== undefined && (
              <div className="flex items-center justify-between">
                <span>Answer Score:</span>
                <span className="font-semibold">
                  {Math.round(message.answer_score)}/100
                </span>
              </div>
            )}
            {message.can_proceed !== undefined && (
              <div className="flex items-center justify-between">
                <span>Ready to Proceed:</span>
                <span
                  className={`font-semibold ${
                    message.can_proceed ? 'text-green-600' : 'text-amber-600'
                  }`}
                >
                  {message.can_proceed ? '✓ Yes' : '⚠ Reask Recommended'}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Reasoning & Decision Trace */}
      {(message.reasoning || message.decision_trace?.length) && (
        <div className="rounded-lg bg-gradient-to-r from-green-50 to-emerald-50 p-3">
          <div className="text-[11px] font-semibold text-slate-600 uppercase tracking-widest">
            Decision Reasoning
          </div>
          {message.reasoning && (
            <p className="mt-2 text-[12px] leading-relaxed text-slate-700">
              {message.reasoning}
            </p>
          )}
          {message.decision_trace?.length && (
            <div className="mt-2 space-y-1">
              <div className="text-[11px] font-medium text-slate-600">
                Evaluation Steps:
              </div>
              <ul className="space-y-1 text-[11px] text-slate-600">
                {message.decision_trace.map((step, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-green-500" />
                    <span>{step}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Improvement Suggestions */}
      {message.improvement_suggestion && (
        <div className="rounded-lg bg-gradient-to-r from-purple-50 to-pink-50 p-3">
          <div className="text-[11px] font-semibold text-slate-600 uppercase tracking-widest">
            💡 Suggestion for Improvement
          </div>
          <p className="mt-2 text-[12px] leading-relaxed text-slate-700">
            {message.improvement_suggestion}
          </p>
        </div>
      )}

      {/* Bias & Fairness Warnings - Enhanced */}
      {message.bias_warnings?.length && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <div className="text-[11px] font-semibold text-amber-900 uppercase tracking-widest">
            ⚠ Fairness & Bias Alert
          </div>
          <div className="mt-2 space-y-1 text-[12px] text-amber-800">
            <p className="font-medium">
              Potential bias signals detected in job description:
            </p>
            <div className="flex flex-wrap gap-1 mt-1">
              {message.bias_warnings.map((warning, i) => (
                <span
                  key={i}
                  className="inline-block bg-white bg-opacity-50 px-2 py-1 rounded text-[11px] font-medium"
                >
                  {warning.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
            <p className="mt-2 text-[11px] italic text-amber-700">
              These signals have been flagged for review to help ensure inclusive hiring practices 
              aligned with responsible AI and anti-discrimination principles.
            </p>
          </div>
        </div>
      )}

      {/* Governance Flags */}
      {message.governance_flags?.length && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3">
          <div className="text-[11px] font-semibold text-red-900 uppercase tracking-widest">
            🔒 Governance Notice
          </div>
          <div className="mt-2 text-[12px] text-red-800">
            <ul className="ml-3 space-y-0.5">
              {message.governance_flags.map((flag, i) => (
                <li key={i} className="list-disc">
                  <span className="capitalize">{flag.replace(/_/g, ' ')}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Human Review Recommendation */}
      {message.requires_human_review && (
        <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-3">
          <div className="text-[11px] font-semibold text-indigo-900 uppercase tracking-widest">
            ℹ Human Review Recommended
          </div>
          <p className="mt-1 text-[12px] text-indigo-800">
            This response has been flagged for manual review by our compliance team to
            ensure alignment with responsible AI governance principles.
          </p>
        </div>
      )}
    </div>
  );
};
