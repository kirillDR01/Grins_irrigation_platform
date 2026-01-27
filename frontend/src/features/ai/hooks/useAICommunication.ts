/**
 * useAICommunication hook
 * 
 * Manages AI communication draft state, loading, error handling,
 * and send/schedule actions
 */

import { useState, useCallback } from 'react';
import { aiApi } from '../api/aiApi';
import type { CommunicationDraftRequest, CommunicationDraft } from '../types';

export interface UseAICommunicationReturn {
  draft: CommunicationDraft | null;
  isLoading: boolean;
  error: string | null;
  auditLogId: string | null;
  generateDraft: (request: CommunicationDraftRequest) => Promise<void>;
  sendNow: (draftId: string) => Promise<void>;
  scheduleLater: (draftId: string, scheduledFor: string) => Promise<void>;
  clearDraft: () => void;
}

export function useAICommunication(): UseAICommunicationReturn {
  const [draft, setDraft] = useState<CommunicationDraft | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [auditLogId, setAuditLogId] = useState<string | null>(null);

  const generateDraft = useCallback(async (request: CommunicationDraftRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await aiApi.draftCommunication(request);
      setDraft(response.draft);
      setAuditLogId(response.audit_log_id);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate draft';
      setError(errorMessage);
      setDraft(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const sendNow = useCallback(async (draftId: string) => {
    setIsLoading(true);
    setError(null);

    try {
      // TODO: Implement actual send API call
      console.log('Sending draft:', draftId);
      // For now, just clear the draft after "sending"
      setDraft(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send message';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const scheduleLater = useCallback(async (draftId: string, scheduledFor: string) => {
    setIsLoading(true);
    setError(null);

    try {
      // TODO: Implement actual schedule API call
      console.log('Scheduling draft:', draftId, 'for', scheduledFor);
      // For now, just clear the draft after "scheduling"
      setDraft(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to schedule message';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearDraft = useCallback(() => {
    setDraft(null);
    setError(null);
    setAuditLogId(null);
  }, []);

  return {
    draft,
    isLoading,
    error,
    auditLogId,
    generateDraft,
    sendNow,
    scheduleLater,
    clearDraft,
  };
}
