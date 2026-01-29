/**
 * Hook for applying a generated schedule.
 * Creates appointments from the schedule assignments.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { scheduleGenerationApi } from '../api/scheduleGenerationApi';
import type { ApplyScheduleRequest, ApplyScheduleResponse } from '../types';

export function useApplySchedule() {
  const queryClient = useQueryClient();

  return useMutation<ApplyScheduleResponse, Error, ApplyScheduleRequest>({
    mutationFn: (request) => scheduleGenerationApi.applySchedule(request),
    onSuccess: () => {
      // Invalidate appointment queries to refresh the calendar
      queryClient.invalidateQueries({ queryKey: ['appointments'] });
      queryClient.invalidateQueries({ queryKey: ['weekly-schedule'] });
      queryClient.invalidateQueries({ queryKey: ['daily-schedule'] });
    },
  });
}
