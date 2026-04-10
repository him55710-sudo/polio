import { useEffect, useRef, useState, useCallback } from 'react';
import { api } from '../lib/api';

/**
 * useAsyncJob 옵션 인터페이스
 */
interface UseAsyncJobOptions<T> {
  /** 폴링할 API 엔드포인트 URL. null이거나 undefined면 폴링을 시작하지 않음. */
  url: string | null | undefined;
  /** 폴링 간격 (기본값: 2000ms) */
  intervalMs?: number;
  /** 작업이 완료(성공 또는 실패 등 최종 상태)되었는지 판단하는 함수 */
  isTerminal: (data: T) => boolean;
  /** 폴링 성공 시 호출될 콜백 */
  onSuccess?: (data: T) => void;
  /** 에러 발생 시 호출될 콜백 */
  onError?: (error: any) => void;
  /** 폴링 활성화 여부 */
  enabled?: boolean;
}

/**
 * 특정 비동기 작업의 상태를 주기적으로 체크(Polling)하는 커스텀 훅
 */
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
  const [error, setError] = useState<any>(null);

  // 폴링 취소를 위한 타이머 참조
  const timerRef = useRef<number | null>(null);
  // 메모리 누수 방지를 위한 취소 플래그
  const isCancelledRef = useRef<boolean>(false);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const poll = useCallback(async () => {
    if (!url || isCancelledRef.current) return;

    try {
      const result = await api.get<T>(url);
      
      if (isCancelledRef.current) return;
      
      setData(result);
      
      if (isTerminal(result)) {
        onSuccess?.(result);
        setIsLoading(false);
        clearTimer();
      } else {
        timerRef.current = window.setTimeout(poll, intervalMs);
      }
    } catch (err) {
      if (isCancelledRef.current) return;
      
      setError(err);
      onError?.(err);
      setIsLoading(false);
      clearTimer();
    }
  }, [url, intervalMs, isTerminal, onSuccess, onError, clearTimer]);

  useEffect(() => {
    isCancelledRef.current = false;
    
    if (enabled && url) {
      setIsLoading(true);
      setError(null);
      poll();
    } else {
      setIsLoading(false);
      clearTimer();
    }

    return () => {
      isCancelledRef.current = true;
      clearTimer();
    };
  }, [enabled, url, poll, clearTimer]);

  return {
    data,
    isLoading,
    error,
    setData, // 수동으로 상태 업데이트가 필요한 경우를 위해 노출
  };
}
