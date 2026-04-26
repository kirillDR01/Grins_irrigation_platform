/**
 * Per-type unacknowledged-alert counts for dashboard cards (gap-14).
 *
 * Single round-trip to GET /api/v1/alerts/counts feeds every per-type
 * card on the dashboard. 60s refetchInterval mirrors the cadence of
 * other dashboard widgets so all surfaces refresh together.
 */
import { useQuery } from '@tanstack/react-query';

import { alertsApi } from '@/features/communications/api/alertsApi';

export const alertKeys = {
  all: ['alerts'] as const,
  lists: () => [...alertKeys.all, 'list'] as const,
  list: (params: Record<string, unknown> | undefined) =>
    [...alertKeys.lists(), params ?? {}] as const,
  counts: () => [...alertKeys.all, 'counts'] as const,
};

export function useAlertCounts() {
  return useQuery({
    queryKey: alertKeys.counts(),
    queryFn: () => alertsApi.counts(),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}
