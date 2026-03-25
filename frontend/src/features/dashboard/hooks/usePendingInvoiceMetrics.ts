/**
 * Hook to fetch pending invoice metrics (count + total amount).
 * Calls GET /api/v1/invoices/metrics/pending.
 *
 * Validates: Requirements 5.1, 5.2
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/core/api/client';

export interface PendingInvoiceMetricsResponse {
  count: number;
  total_amount: string;
}

export const pendingInvoiceMetricsKeys = {
  all: ['invoices'] as const,
  pendingMetrics: () => [...pendingInvoiceMetricsKeys.all, 'metrics', 'pending'] as const,
};

async function fetchPendingInvoiceMetrics(): Promise<PendingInvoiceMetricsResponse> {
  const response = await apiClient.get<PendingInvoiceMetricsResponse>(
    '/invoices/metrics/pending'
  );
  return response.data;
}

/**
 * Fetches pending invoice count and total amount.
 * Refreshes every 60s, stale after 30s.
 */
export function usePendingInvoiceMetrics() {
  return useQuery({
    queryKey: pendingInvoiceMetricsKeys.pendingMetrics(),
    queryFn: fetchPendingInvoiceMetrics,
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });
}
