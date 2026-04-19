import React from 'react';

export const AlignmentStep: React.FC<{
  jd: string;
  onChangeJD: (val: string) => void;
  onAnalyze: () => void;
  isLoading: boolean;
}> = ({ jd, onChangeJD, onAnalyze, isLoading }) => {
  const MAX_JD_LENGTH = 20000;

  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-400 space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Role Fit Definition</h3>
        <span
          className={`text-[10px] font-medium ${jd.length > MAX_JD_LENGTH ? "text-red-500" : "text-slate-400"}`}
        >
          {jd.length.toLocaleString()} / {MAX_JD_LENGTH.toLocaleString()}
        </span>
      </div>
      <textarea
        className="w-full h-48 p-4 rounded-xl bg-white border border-slate-200 focus:ring-1 focus:ring-slate-900 focus:outline-none text-xs transition-all scrollbar-thin"
        placeholder="Paste the target job description here..."
        value={jd}
        maxLength={MAX_JD_LENGTH}
        onChange={(e) => onChangeJD(e.target.value)}
      />
      <button
        onClick={onAnalyze}
        disabled={!jd || isLoading}
        className="w-full bg-slate-900 disabled:opacity-50 text-white text-[13px] font-semibold py-3 rounded-lg shadow-sm hover:bg-slate-800 transition-all"
      >
        {isLoading ? "Scanning Requirements..." : "Analyze Market Fit"}
      </button>
    </div>
  );
};
