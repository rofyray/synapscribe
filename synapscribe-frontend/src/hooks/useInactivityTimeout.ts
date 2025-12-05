import { useEffect, useRef, useCallback } from 'react';

interface UseInactivityTimeoutOptions {
  timeoutMs: number;
  onTimeout: () => void;
  enabled?: boolean;
}

export function useInactivityTimeout({
  timeoutMs,
  onTimeout,
  enabled = true,
}: UseInactivityTimeoutOptions) {
  const timeoutRef = useRef<number | null>(null);
  const lastActivityRef = useRef<number>(Date.now());

  const resetTimeout = useCallback(() => {
    if (!enabled) return;

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    lastActivityRef.current = Date.now();

    timeoutRef.current = window.setTimeout(() => {
      onTimeout();
    }, timeoutMs);
  }, [timeoutMs, onTimeout, enabled]);

  useEffect(() => {
    if (enabled) {
      resetTimeout();
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [enabled, resetTimeout]);

  return {
    resetTimeout,
    getLastActivity: () => lastActivityRef.current,
    getRemainingTime: () => {
      const elapsed = Date.now() - lastActivityRef.current;
      return Math.max(0, timeoutMs - elapsed);
    },
  };
}
