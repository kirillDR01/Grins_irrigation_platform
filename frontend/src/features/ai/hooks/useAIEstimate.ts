/**
 * useAIEstimate hook
 * 
 * Manages AI estimate generation state and quote adjustment
 */

import { useState, useCallback } from 'react';
import { aiApi } from '../api/aiApi';
import type { EstimateGenerateRequest, EstimateGenerateResponse } from '../types';

export interface UseAIEstimateReturn {
  estimate: EstimateGenerateResponse | null;
  isLoading: boolean;
  error: string | null;
  auditLogId: string | null;
  generateEstimate: (request: EstimateGenerateRequest) => Promise<void>;
  adjustQuote: (newPrice: string) => void;
  clearEstimate: () => void;
}

export function useAIEstimate(): UseAIEstimateReturn {
  const [estimate, setEstimate] = useState<EstimateGenerateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [auditLogId, setAuditLogId] = useState<string | null>(null);

  const generateEstimate = useCallback(async (request: EstimateGenerateRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await aiApi.generateEstimate(request);
      setEstimate(response);
      setAuditLogId(response.audit_log_id);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate estimate';
      setError(errorMessage);
      setEstimate(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const adjustQuote = useCallback((newPrice: string) => {
    if (estimate) {
      setEstimate({
        ...estimate,
        recommended_price: newPrice,
      });
    }
  }, [estimate]);

  const clearEstimate = useCallback(() => {
    setEstimate(null);
    setError(null);
    setAuditLogId(null);
  }, []);

  return {
    estimate,
    isLoading,
    error,
    auditLogId,
    generateEstimate,
    adjustQuote,
    clearEstimate,
  };
}
