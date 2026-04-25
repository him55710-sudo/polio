import { useCallback, useMemo, useState } from 'react';

export type WorkshopSessionStatus = 'idle' | 'loading' | 'ready' | 'error';

export function useWorkshopSession<TSession = unknown>(initialSession: TSession | null = null) {
  const [session, setSession] = useState<TSession | null>(initialSession);
  const [status, setStatus] = useState<WorkshopSessionStatus>(initialSession ? 'ready' : 'idle');
  const [error, setError] = useState<unknown>(null);

  const runWithSessionLoading = useCallback(async <T,>(task: () => Promise<T>) => {
    setStatus('loading');
    setError(null);
    try {
      const result = await task();
      setStatus('ready');
      return result;
    } catch (caught) {
      setError(caught);
      setStatus('error');
      throw caught;
    }
  }, []);

  return useMemo(
    () => ({
      session,
      setSession,
      status,
      setStatus,
      error,
      setError,
      runWithSessionLoading,
    }),
    [error, runWithSessionLoading, session, status],
  );
}
