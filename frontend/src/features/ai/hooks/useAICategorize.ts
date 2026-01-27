/**
 * useAICategorize hook
 * 
 * Manages AI job categorization state, bulk approval actions, and error handling
 */

import { useState, useCallback } from 'react';
import { aiApi } from '../api/aiApi';
import type { JobCategorizationRequest, JobCategorization, CategorizationSummary } from '../types';

export interface UseAICategorizeReturn {
  categorizations: JobCategorization[];
  summary: CategorizationSummary | null;
  isLoading: boolean;
  error: string | null;
  auditLogId: string | null;
  categorizeJobs: (request: JobCategorizationRequest) => Promise<void>;
  approveBulk: (jobIds: string[]) => Promise<void>;
  clearCategorizations: () => void;
}

export function useAICategorize(): UseAICategorizeReturn {
  const [categorizations, setCategorizations] = useState<JobCategorization[]>([]);
  const [summary, setSummary] = useState<CategorizationSummary | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [auditLogId, setAuditLogId] = useState<string | null>(null);

  const categorizeJobs = useCallback(async (request: JobCategorizationRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await aiApi.categorizeJobs(request);
      setCategorizations(response.categorizations);
      setSummary(response.summary);
      setAuditLogId(response.audit_log_id);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to categorize jobs';
      setError(errorMessage);
      setCategorizations([]);
      setSummary(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const approveBulk = useCallback(async (jobIds: string[]) => {
    setIsLoading(true);
    setError(null);

    try {
      // Remove approved jobs from categorizations
      setCategorizations(prev => prev.filter(cat => !jobIds.includes(cat.job_id)));
      
      // Update summary
      if (summary) {
        setSummary({
          ...summary,
          total_jobs: summary.total_jobs - jobIds.length,
          ready_to_schedule: Math.max(0, summary.ready_to_schedule - jobIds.length),
        });
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to approve jobs';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [summary]);

  const clearCategorizations = useCallback(() => {
    setCategorizations([]);
    setSummary(null);
    setError(null);
    setAuditLogId(null);
  }, []);

  return {
    categorizations,
    summary,
    isLoading,
    error,
    auditLogId,
    categorizeJobs,
    approveBulk,
    clearCategorizations,
  };
}
