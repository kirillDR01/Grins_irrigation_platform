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
  enabled?: boolean;
}

export function useUnassignedJobExplanation({
  job,
  enabled = true,
}: UseUnassignedJobExplanationOptions) {
  // Build request matching backend UnassignedJobExplanationRequest schema
  // Note: UnassignedJobResponse from schedule generation doesn't have all fields,
  // so we provide sensible defaults for the explanation request
  const request: UnassignedJobExplanationRequest = {
    job_id: job.job_id,
    job_type: job.service_type, // Map service_type to job_type
    customer_name: job.customer_name,
    city: 'Unknown', // Not available in UnassignedJobResponse
    estimated_duration_minutes: 60, // Default since not available
    priority: 'normal', // Default since not available
    requires_equipment: [], // Default since not available
    constraint_violations: job.reason ? [job.reason] : [], // Use reason as constraint violation
  };

  const query = useQuery({
    queryKey: ['unassigned-job-explanation', job.job_id],
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
