import React from "react";
import { WorkflowStatus } from "../types";

interface StepIndicatorProps {
  currentStatus: WorkflowStatus;
  onStepClick: (status: WorkflowStatus) => void;
}

const steps = [
  { status: WorkflowStatus.IDLE, label: "Upload" },
  { status: WorkflowStatus.CRITIQUING, label: "Critic" },
  { status: WorkflowStatus.ANALYZING_CONTENT, label: "Content" },
  { status: WorkflowStatus.ALIGNING_JD, label: "Matching" },
  { status: WorkflowStatus.INTERVIEWING, label: "Interview" },
];

export const StepIndicator: React.FC<StepIndicatorProps> = ({
  currentStatus,
  onStepClick,
}) => {
  const getStepIndex = (status: WorkflowStatus) => {
    if (status === WorkflowStatus.AWAITING_CRITIC_APPROVAL) return 1;
    if (status === WorkflowStatus.AWAITING_CONTENT_APPROVAL) return 2;
    if (status === WorkflowStatus.AWAITING_ALIGNMENT_APPROVAL) return 3;
    if (
      status === WorkflowStatus.INTERVIEWING ||
      status === WorkflowStatus.COMPLETED ||
      status === WorkflowStatus.SELECTING_INTERVIEW_MODE ||
      status === WorkflowStatus.DEBUG_VOICE
    )
      return 4;
    return steps.findIndex((s) => s.status === status);
  };

  const currentIndex = getStepIndex(currentStatus);

  return (
    <div className="flex items-center justify-center gap-1 w-full min-w-max">
      {steps.map((step, idx) => {
        const isActive = idx <= currentIndex;
        const isCurrent = idx === currentIndex;
        const isFuture = idx > currentIndex;

        // Extract nested ternary operations for better readability
        const buttonClasses = isFuture
          ? "cursor-not-allowed opacity-50"
          : "hover:bg-slate-100 cursor-pointer active:scale-95";

        let circleClasses: string;

        if (isCurrent) {
          circleClasses = "bg-slate-900 text-white shadow-md ring-2 ring-slate-900/10";
        } else if (isActive) {
          circleClasses = "bg-slate-200 text-slate-700";
        } else {
          circleClasses = "bg-transparent border border-slate-200 text-slate-300";
        }

        let textClasses: string;

        if (isCurrent) {
          textClasses = "text-slate-900";
        } else if (isActive) {
          textClasses = "text-slate-500";
        } else {
          textClasses = "text-slate-300";
        }

        return (
          <React.Fragment key={step.label}>
            <button
              onClick={() => !isFuture && onStepClick(step.status)}
              disabled={isFuture}
              className={`flex items-center gap-2.5 py-1.5 px-3 rounded-md transition-all focus:outline-none ${buttonClasses}`}
            >
              <div
                className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold transition-all duration-300 ${circleClasses}`}
              >
                {idx + 1}
              </div>
              <span
                className={`text-[11px] font-semibold whitespace-nowrap transition-colors duration-300 ${textClasses}`}
              >
                {step.label}
              </span>
            </button>
            {idx < steps.length - 1 && (
              <div
                className={`w-8 md:w-16 lg:w-20 h-[1px] transition-colors duration-500 ${idx < currentIndex ? "bg-slate-300" : "bg-slate-200"
                  }`}
              ></div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
