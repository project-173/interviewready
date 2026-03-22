import React from 'react';

interface LoadingStateProps {
  isLoading: boolean;
  message?: string;
  progress?: number;
  steps?: string[];
  currentStep?: number;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ 
  isLoading, 
  message = "Processing...", 
  progress,
  steps = [],
  currentStep = 0
}) => {
  if (!isLoading) return null;

  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 border border-slate-200">
        {/* Loading Animation */}
        <div className="flex justify-center mb-6">
          <div className="relative">
            <div className="w-16 h-16 border-4 border-slate-200 rounded-full"></div>
            <div className="absolute top-0 left-0 w-16 h-16 border-4 border-slate-900 rounded-full border-t-transparent animate-spin"></div>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-8 h-8 bg-slate-900 rounded-full animate-pulse"></div>
            </div>
          </div>
        </div>

        {/* Main Message */}
        <div className="text-center mb-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-2">{message}</h3>
          <p className="text-sm text-slate-500">AI agents are analyzing your request</p>
        </div>

        {/* Progress Bar */}
        {progress !== undefined && (
          <div className="mb-6">
            <div className="flex justify-between text-xs text-slate-500 mb-2">
              <span>Progress</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div 
                className="bg-slate-900 h-2 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* Steps */}
        {steps.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Processing Steps</p>
            <div className="space-y-2">
              {steps.map((step, index) => (
                <div 
                  key={index} 
                  className={`flex items-center gap-3 text-sm ${
                    index < currentStep 
                      ? 'text-green-600' 
                      : index === currentStep 
                      ? 'text-slate-900 font-medium' 
                      : 'text-slate-400'
                  }`}
                >
                  <div className={`w-4 h-4 rounded-full flex items-center justify-center ${
                    index < currentStep 
                      ? 'bg-green-100 border-2 border-green-500' 
                      : index === currentStep 
                      ? 'bg-slate-900 border-2 border-slate-900' 
                      : 'bg-slate-100 border-2 border-slate-300'
                  }`}>
                    {index < currentStep ? (
                      <svg className="w-2 h-2 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    ) : index === currentStep ? (
                      <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></div>
                    ) : (
                      <div className="w-1.5 h-1.5 bg-slate-400 rounded-full"></div>
                    )}
                  </div>
                  <span className="truncate">{step}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Cancel Hint */}
        <div className="mt-6 pt-4 border-t border-slate-100">
          <p className="text-xs text-slate-400 text-center">
            This may take a few moments...
          </p>
        </div>
      </div>
    </div>
  );
};
