/**
 * Hook to fetch job status metrics for the 6 dashboard categories.
 * Calls GET /api/v1/jobs/metrics/by-status.
 *
 * Validates: Requirements 6.1
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/core/api/client';

export interface JobStatusMetricsResponse {
  new_requests: number;
  estimates: number;
  pending_approval: number;
  to_be_scheduled: number;
  in_progress: number;
  complete: number;
}

export const jobStatusMetricsKeys = {
  all: ['jobs'] as const,
  statusMetrics: () => [...jobStatusMetricsKeys.all, 'metrics', 'by-status'] as const,
};

async function fetchJobStatusMetrics(): Promise<JobStatusMetricsResponse> {
  const response = await apiClient.get<JobStatusMetricsResponse>(
    '/jobs/metrics/by-status'
  );
  return response.data;
}

/**
 * Fetches job counts for the 6 dashboard status categories.
 * Refreshes every 60s, stale after 30s.
 */
export function useJobStatusMetrics() {
  return useQuery({
    queryKey: jobStatusMetricsKeys.statusMetrics(),
    queryFn: fetchJobStatusMetrics,
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });
}
