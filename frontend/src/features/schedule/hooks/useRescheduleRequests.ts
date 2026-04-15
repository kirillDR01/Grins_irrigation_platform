/**
 * Hooks for reschedule requests.
 * Validates: CRM Changes Update 2 Req 25.1, 25.2, 25.3, 25.4
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { rescheduleApi } from '../api/rescheduleApi';

export const rescheduleKeys = {
  all: ['reschedule-requests'] as const,
  list: (status?: string) => [...rescheduleKeys.all, 'list', status] as const,
};

export function useRescheduleRequests(status?: string) {
  return useQuery({
    queryKey: rescheduleKeys.list(status),
    queryFn: () => rescheduleApi.list(status),
  });
}

export function useResolveRescheduleRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      rescheduleApi.resolve(id, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rescheduleKeys.all });
    },
  });
}
