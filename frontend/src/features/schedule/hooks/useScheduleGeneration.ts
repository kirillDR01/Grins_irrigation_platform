/**
 * React Query hooks for schedule generation.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { scheduleGenerationApi } from '../api/scheduleGenerationApi';
import type { ScheduleGenerateRequest } from '../types';

export const scheduleGenerationKeys = {
  all: ['schedule-generation'] as const,
  capacity: (date: string) =>
    [...scheduleGenerationKeys.all, 'capacity', date] as const,
  status: (date: string) =>
    [...scheduleGenerationKeys.all, 'status', date] as const,
};

export function useScheduleCapacity(date: string) {
  return useQuery({
    queryKey: scheduleGenerationKeys.capacity(date),
    queryFn: () => scheduleGenerationApi.getCapacity(date),
    enabled: !!date,
  });
}

export function useScheduleStatus(date: string) {
  return useQuery({
    queryKey: scheduleGenerationKeys.status(date),
    queryFn: () => scheduleGenerationApi.getStatus(date),
    enabled: !!date,
  });
}

export function useGenerateSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: ScheduleGenerateRequest) =>
      scheduleGenerationApi.generate(request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: scheduleGenerationKeys.capacity(variables.schedule_date),
      });
      queryClient.invalidateQueries({
        queryKey: scheduleGenerationKeys.status(variables.schedule_date),
      });
      queryClient.invalidateQueries({ queryKey: ['appointments'] });
    },
  });
}

export function usePreviewSchedule() {
  return useMutation({
    mutationFn: (request: ScheduleGenerateRequest) =>
      scheduleGenerationApi.preview(request),
  });
}
