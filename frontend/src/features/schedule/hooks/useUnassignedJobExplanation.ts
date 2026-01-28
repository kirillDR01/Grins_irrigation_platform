/**
 * Hook for fetching unassigned job explanations.
 */

import { useQuery } from '@tanstack/react-query';
import { scheduleGenerationApi } from '../api/scheduleGenerationApi';
import type {
  UnassignedJobExplanationRequest,
  UnassignedJobExplanationResponse,
} from '../types/explanation';
import type { UnassignedJobResponse } from '../types';

interface UseUnassignedJobExplanationOptions {
  job: UnassignedJobResponse;
  scheduleDate: string;
  availableStaff: string[];
  enabled?: boolean;
}

export function useUnassignedJobExplanation({
  job,
  scheduleDate,
  availableStaff,
  enabled = true,
}: UseUnassignedJobExplanationOptions) {
  const request: UnassignedJobExplanationRequest = {
    job_id: job.job_id,
    customer_name: job.customer_name,
    service_type: job.service_type,
    city: job.city || null,
    duration_minutes: job.duration_minutes,
    schedule_date: scheduleDate,
    available_staff: availableStaff,
    reason: job.reason,
  };

  const query = useQuery({
    queryKey: ['unassigned-job-explanation', job.job_id, scheduleDate],
    queryFn: () => scheduleGenerationApi.explainUnassignedJob(request),
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  });

  return {
    explanation: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}
