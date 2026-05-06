import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  salesRescheduleApi,
  type SalesRescheduleRequestDetail,
} from '../api/salesRescheduleApi';

export const estimateRescheduleKeys = {
  all: ['sales', 'reschedule-requests'] as const,
  list: (status: 'open' | 'resolved') =>
    [...estimateRescheduleKeys.all, status] as const,
};

/**
 * Subscribe to the open / resolved sales-side reschedule queue.
 *
 * Mirror of ``useRescheduleRequests`` in the schedule feature, scoped to
 * estimate visits via ``sales_calendar_event_id IS NOT NULL``.
 */
export function useEstimateRescheduleRequests(
  status: 'open' | 'resolved' = 'open',
) {
  return useQuery<SalesRescheduleRequestDetail[]>({
    queryKey: estimateRescheduleKeys.list(status),
    queryFn: () => salesRescheduleApi.list(status),
    staleTime: 30_000,
  });
}

export function useResolveEstimateReschedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (requestId: string) => salesRescheduleApi.resolve(requestId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: estimateRescheduleKeys.all });
    },
  });
}

export function useRescheduleEstimateFromRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      requestId,
      body,
    }: {
      requestId: string;
      body: {
        scheduled_date: string;
        start_time?: string | null;
        end_time?: string | null;
      };
    }) => salesRescheduleApi.rescheduleFromRequest(requestId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: estimateRescheduleKeys.all });
    },
  });
}
