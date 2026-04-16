import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';

interface UseAsyncJobOptions<T> {
  url: string | null | undefined;
  intervalMs?: number;
  isTerminal: (data: T) => boolean;
  onSuccess?: (data: T) => void;
  onError?: (error: unknown) => void;
  enabled?: boolean;
}

export function useAsyncJob<T>({
  url,
  intervalMs = 2000,
  isTerminal,
  onSuccess,
  onError,
  enabled = true,
}: UseAsyncJobOptions<T>) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const timerRef = useRef<number | null>(null);
  const isCancelledRef = useRef(false);
  const requestKeyRef = useRef(0);
  const activeUrlRef = useRef<string | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => {
    isCancelledRef.current = false;
    requestKeyRef.current += 1;
    const requestKey = requestKeyRef.current;
    const requestUrl = enabled && url ? url : null;
    activeUrlRef.current = requestUrl;

    setData(null);
    setError(null);

    if (!requestUrl) {
      setIsLoading(false);
      clearTimer();
      return () => {
        isCancelledRef.current = true;
        clearTimer();
      };
    }

    setIsLoading(true);

    const poll = async (): Promise<void> => {
      if (
        isCancelledRef.current ||
        requestKey !== requestKeyRef.current ||
        requestUrl !== activeUrlRef.current
      ) {
        return;
      }

      try {
        const result = await api.get<T>(requestUrl);
        if (
          isCancelledRef.current ||
          requestKey !== requestKeyRef.current ||
          requestUrl !== activeUrlRef.current
        ) {
          return;
        }

        setData(result);

        if (isTerminal(result)) {
          onSuccess?.(result);
          setIsLoading(false);
          clearTimer();
          return;
        }

        timerRef.current = window.setTimeout(() => {
          void poll();
        }, intervalMs);
      } catch (nextError) {
        if (
          isCancelledRef.current ||
          requestKey !== requestKeyRef.current ||
          requestUrl !== activeUrlRef.current
        ) {
          return;
        }

        setError(nextError);
        onError?.(nextError);
        setIsLoading(false);
        clearTimer();
      }
    };

    void poll();

    return () => {
      isCancelledRef.current = true;
      clearTimer();
    };
  }, [enabled, url, intervalMs, isTerminal, onSuccess, onError, clearTimer]);

  return {
    data,
    isLoading,
    error,
    setData,
  };
}
