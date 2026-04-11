import React, { createContext, useContext, useEffect, useState } from 'react';
import { api, RuntimeCapabilities } from '../lib/api';

interface RuntimeContextType {
  capabilities: RuntimeCapabilities | null;
  isLoading: boolean;
  error: Error | null;
}

const RuntimeContext = createContext<RuntimeContextType | undefined>(undefined);

export const RuntimeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [capabilities, setCapabilities] = useState<RuntimeCapabilities | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    async function fetchCapabilities() {
      try {
        const caps = await api.getRuntimeCapabilities();
        setCapabilities(caps);
      } catch (err) {
        console.error('Failed to fetch runtime capabilities:', err);
        setError(err instanceof Error ? err : new Error('Unknown error'));
        
        // Fallback for safety if API fails
        setCapabilities({
          allow_inline_job_processing: true,
          async_jobs_inline_dispatch: true,
          serverless_runtime: false,
          recommended_document_parse_mode: 'sync',
          recommended_diagnosis_mode: 'async',
          requires_explicit_process_kicking: false
        });
      } finally {
        setIsLoading(false);
      }
    }

    fetchCapabilities();
  }, []);

  return (
    <RuntimeContext.Provider value={{ capabilities, isLoading, error }}>
      {children}
    </RuntimeContext.Provider>
  );
};

export const useRuntime = () => {
  const context = useContext(RuntimeContext);
  if (context === undefined) {
    throw new Error('useRuntime must be used within a RuntimeProvider');
  }
  return context;
};
