/**
 * Dashboard widget count hook for the informal-opt-out queue (Gap 06).
 *
 * Reuses the same query key as the queue page so a single network
 * fetch feeds both surfaces (TanStack Query de-dupes by queryKey).
 */
import { useQuery } from '@tanstack/react-query';

import { alertsApi } from '@/features/communications/api/alertsApi';
import { informalOptOutQueueKeys } from '@/features/communications/hooks/useInformalOptOutQueue';

export function useInformalOptOutCount() {
  return useQuery({
    queryKey: informalOptOutQueueKeys.list(),
    queryFn: () => alertsApi.list({ type: 'informal_opt_out' }),
    staleTime: 30_000,
    select: (data) => data.items.length,
  });
}
