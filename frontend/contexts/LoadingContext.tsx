import React, { createContext, useContext, useState, ReactNode } from 'react';

interface LoadingContextType {
  isLoading: boolean;
  message: string;
  progress: number;
  steps: string[];
  currentStep: number;
  setLoading: (loading: boolean) => void;
  setMessage: (message: string) => void;
  setProgress: (progress: number) => void;
  setSteps: (steps: string[]) => void;
  setCurrentStep: (step: number) => void;
  startLoading: (message?: string, steps?: string[]) => void;
  updateProgress: (progress: number, step?: number) => void;
  stopLoading: () => void;
}

const LoadingContext = createContext<LoadingContextType | undefined>(undefined);

export const useLoading = () => {
  const context = useContext(LoadingContext);
  if (!context) {
    throw new Error('useLoading must be used within a LoadingProvider');
  }
  return context;
};

interface LoadingProviderProps {
  children: ReactNode;
}

export const LoadingProvider: React.FC<LoadingProviderProps> = ({ children }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('Processing...');
  const [progress, setProgress] = useState(0);
  const [steps, setSteps] = useState<string[]>([]);
  const [currentStep, setCurrentStep] = useState(0);

  const setLoading = (loading: boolean) => setIsLoading(loading);
  
  const startLoading = (message?: string, steps?: string[]) => {
    setIsLoading(true);
    setMessage(message || 'Processing...');
    setProgress(0);
    setSteps(steps || []);
    setCurrentStep(0);
  };

  const updateProgress = (progress: number, step?: number) => {
    setProgress(progress);
    if (step !== undefined) {
      setCurrentStep(step);
    }
  };

  const stopLoading = () => {
    setIsLoading(false);
    setProgress(0);
    setCurrentStep(0);
  };

  return (
    <LoadingContext.Provider
      value={{
        isLoading,
        message,
        progress,
        steps,
        currentStep,
        setLoading,
        setMessage,
        setProgress,
        setSteps,
        setCurrentStep,
        startLoading,
        updateProgress,
        stopLoading,
      }}
    >
      {children}
    </LoadingContext.Provider>
  );
};
