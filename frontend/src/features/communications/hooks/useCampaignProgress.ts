import { useQuery } from '@tanstack/react-query';
import { campaignsApi } from '../api/campaignsApi';
import { campaignKeys } from './useCampaigns';

/** Poll campaign stats for progress tracking (refetches every 5s while sending) */
export function useCampaignProgress(id: string, enabled = true) {
  return useQuery({
    queryKey: campaignKeys.stats(id),
    queryFn: () => campaignsApi.getStats(id),
    enabled: !!id && enabled,
    refetchInterval: enabled ? 5000 : false,
  });
}

/** Poll worker health (refetches every 30s) */
export function useWorkerHealth(enabled = true) {
  return useQuery({
    queryKey: campaignKeys.workerHealth(),
    queryFn: () => campaignsApi.getWorkerHealth(),
    enabled,
    refetchInterval: enabled ? 30000 : false,
  });
}
