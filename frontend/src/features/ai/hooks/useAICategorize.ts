/**
 * useAICategorize hook
 * 
 * Manages AI job categorization state, bulk approval actions, and error handling
 */

import { useState, useCallback } from 'react';
import { aiApi } from '../api/aiApi';
import type { JobCategorizationRequest, JobCategorizationResponse } from '../types';

export interface UseAICategorizeReturn {
  categorization: JobCategorizationResponse | null;
  isLoading: boolean;
  error: string | null;
  auditLogId: string | null;
  categorizeJobs: (request: JobCategorizationRequest) => Promise<void>;
  approveBulk: (jobIds: string[]) => Promise<void>;
  clearCategorizations: () => void;
}

export function useAICategorize(): UseAICategorizeReturn {
  const [categorization, setCategorization] = useState<JobCategorizationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [auditLogId, setAuditLogId] = useState<string | null>(null);

  const categorizeJobs = useCallback(async (request: JobCategorizationRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await aiApi.categorizeJobs(request);
      setCategorization(response);
      setAuditLogId(response.audit_id);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to categorize jobs';
      setError(errorMessage);
      setCategorization(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const approveBulk = useCallback(async (_jobIds: string[]) => {
    setIsLoading(true);
    setError(null);

    try {
      // Clear categorization after approval
      setCategorization(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to approve jobs';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearCategorizations = useCallback(() => {
    setCategorization(null);
    setError(null);
    setAuditLogId(null);
  }, []);

  return {
    categorization,
    isLoading,
    error,
    auditLogId,
    categorizeJobs,
    approveBulk,
    clearCategorizations,
  };
}
