import React from 'react';
import { InterviewMode } from '../../types';

export const InterviewModeSelectionStep: React.FC<{
  onSelect: (mode: InterviewMode) => void;
}> = ({ onSelect }) => (
  <div className="animate-in fade-in slide-in-from-bottom-2 duration-400 space-y-8">
    <div className="text-center">
      <h3 className="text-xl font-bold text-slate-900 mb-2">
        Select Interview Format
      </h3>
      <p className="text-sm text-slate-500">
        Choose how you'd like to practice today. This choice is final for this
        session.
      </p>
    </div>

    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <button
        onClick={() => onSelect("CHAT")}
        className="flex flex-col items-center p-8 bg-white border border-slate-200 rounded-2xl hover:border-slate-900 hover:shadow-md transition-all group text-center"
      >
        <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-6 group-hover:bg-slate-900 group-hover:text-white transition-colors">
          <svg
            className="w-8 h-8"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            />
          </svg>
        </div>
        <h4 className="font-bold text-lg mb-2">Text Chat</h4>
        <p className="text-xs text-slate-500 leading-relaxed">
          Standard text-based interface. Best for quick practice or public
          spaces.
        </p>
      </button>

      <button
        onClick={() => onSelect("VOICE")}
        className="flex flex-col items-center p-8 bg-white border border-slate-200 rounded-2xl hover:border-slate-900 hover:shadow-md transition-all group text-center"
      >
        <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-6 group-hover:bg-slate-900 group-hover:text-white transition-colors">
          <svg
            className="w-8 h-8"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
            />
          </svg>
        </div>
        <h4 className="font-bold text-lg mb-2">Organic Voice</h4>
        <p className="text-xs text-slate-500 leading-relaxed">
          Immersive voice simulation. Hands-free conversation with real-time
          audio analysis.
        </p>
      </button>
    </div>
  </div>
);
