import { useQuery } from '@tanstack/react-query';
import { scheduleGenerationApi } from '../api/scheduleGenerationApi';
import type { JobsReadyToScheduleResponse } from '../types';

export function useJobsReadyToSchedule(params?: {
  start_date?: string;
  end_date?: string;
}) {
  return useQuery<JobsReadyToScheduleResponse>({
    queryKey: ['jobs-ready-to-schedule', params],
    queryFn: () => scheduleGenerationApi.getJobsReadyToSchedule(params),
  });
}
