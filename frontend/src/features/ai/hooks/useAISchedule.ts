/**
 * useAISchedule hook
 * 
 * Manages AI schedule generation state, loading, and error handling
 */

import { useState, useCallback } from 'react';
import { aiApi } from '../api/aiApi';
import type { ScheduleGenerateRequest, ScheduleGenerateResponse } from '../types';

export interface UseAIScheduleReturn {
  schedule: ScheduleGenerateResponse | null;
  isLoading: boolean;
  error: string | null;
  auditLogId: string | null;
  generateSchedule: (request: ScheduleGenerateRequest) => Promise<void>;
  regenerate: () => void;
  clearSchedule: () => void;
}

export function useAISchedule(): UseAIScheduleReturn {
  const [schedule, setSchedule] = useState<ScheduleGenerateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [auditLogId, setAuditLogId] = useState<string | null>(null);
  const [lastRequest, setLastRequest] = useState<ScheduleGenerateRequest | null>(null);

  const generateSchedule = useCallback(async (request: ScheduleGenerateRequest) => {
    setIsLoading(true);
    setError(null);
    setLastRequest(request);

    try {
      const response = await aiApi.generateSchedule(request);
      setSchedule(response);
      setAuditLogId(response.audit_id);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate schedule';
      setError(errorMessage);
      setSchedule(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const regenerate = useCallback(() => {
    if (lastRequest) {
      generateSchedule(lastRequest);
    }
  }, [lastRequest, generateSchedule]);

  const clearSchedule = useCallback(() => {
    setSchedule(null);
    setError(null);
    setAuditLogId(null);
    setLastRequest(null);
  }, []);

  return {
    schedule,
    isLoading,
    error,
    auditLogId,
    generateSchedule,
    regenerate,
    clearSchedule,
  };
}
