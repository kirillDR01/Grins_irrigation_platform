/**
 * Hook to fetch the count of unaddressed customer communications.
 * Calls GET /api/v1/communications/unaddressed-count.
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/core/api/client';

interface UnaddressedCountResponse {
  count: number;
}

export const unaddressedCountKeys = {
  all: ['communications'] as const,
  unaddressedCount: () => [...unaddressedCountKeys.all, 'unaddressed-count'] as const,
};

async function fetchUnaddressedCount(): Promise<UnaddressedCountResponse> {
  const response = await apiClient.get<UnaddressedCountResponse>(
    '/communications/unaddressed-count'
  );
  return response.data;
}

/**
 * Fetches the unaddressed communication count.
 * Refreshes every 60s, stale after 30s.
 */
export function useUnaddressedCount() {
  return useQuery({
    queryKey: unaddressedCountKeys.unaddressedCount(),
    queryFn: fetchUnaddressedCount,
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });
}
