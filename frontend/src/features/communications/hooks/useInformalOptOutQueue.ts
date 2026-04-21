/**
 * Informal-opt-out queue hooks (Gap 06).
 *
 * Mirrors the useNoReplyReview pattern: a single list query plus two
 * mutations (confirm / dismiss) that invalidate alert counts, the
 * consent-status key family, and the queue itself.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { alertsApi } from '../api/alertsApi';
import { consentStatusKeys } from '@/features/customers/hooks/useConsentStatus';

export const informalOptOutQueueKeys = {
  all: ['informal-opt-out-queue'] as const,
  list: () => [...informalOptOutQueueKeys.all, 'list'] as const,
};

export function useInformalOptOutQueue() {
  return useQuery({
    queryKey: informalOptOutQueueKeys.list(),
    queryFn: () => alertsApi.list({ type: 'informal_opt_out' }),
    staleTime: 30_000,
  });
}

export function useConfirmInformalOptOut() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (alertId: string) => alertsApi.confirmOptOut(alertId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: informalOptOutQueueKeys.all });
      qc.invalidateQueries({ queryKey: consentStatusKeys.all });
    },
  });
}

export function useDismissInformalOptOut() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (alertId: string) => alertsApi.dismiss(alertId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: informalOptOutQueueKeys.all });
      qc.invalidateQueries({ queryKey: consentStatusKeys.all });
    },
  });
}
