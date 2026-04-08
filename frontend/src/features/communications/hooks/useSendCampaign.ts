import { useMutation, useQueryClient } from '@tanstack/react-query';
import { campaignsApi } from '../api/campaignsApi';
import { campaignKeys } from './useCampaigns';

/** Send a campaign (returns 202 Accepted, background worker drains) */
export function useSendCampaign() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => campaignsApi.send(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: campaignKeys.detail(id) });
      qc.invalidateQueries({ queryKey: campaignKeys.lists() });
    },
  });
}

/** Cancel a campaign (transitions pending recipients to cancelled) */
export function useCancelCampaign() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => campaignsApi.cancel(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: campaignKeys.detail(id) });
      qc.invalidateQueries({ queryKey: campaignKeys.lists() });
    },
  });
}

/** Retry failed recipients (creates new pending rows from failed ones) */
export function useRetryFailed() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => campaignsApi.retryFailed(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: campaignKeys.detail(id) });
      qc.invalidateQueries({ queryKey: campaignKeys.lists() });
      qc.invalidateQueries({ queryKey: campaignKeys.stats(id) });
    },
  });
}
