/**
 * TanStack Query hooks for AI scheduling extensions.
 * Covers capacity forecast (30-criteria), batch generation, utilization, evaluate, and criteria config.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/core/api/client';

// ---- Types ----------------------------------------------------------------

export interface CriterionResult {
  criterion_number: number;
  criterion_name: string;
  score: number;
  weight: number;
  is_hard: boolean;
  is_satisfied: boolean;
  explanation: string;
}

export interface ScheduleEvaluation {
  schedule_date: string;
  total_score: number;
  hard_violations: number;
  criteria_scores: CriterionResult[];
  alerts: string[];
}

export interface CapacityForecastExtended {
  // Existing fields preserved
  date?: string;
  total_jobs?: number;
  total_staff?: number;
  // New 30-criteria analysis fields (optional, additive)
  evaluation?: ScheduleEvaluation;
  utilization_pct?: number;
  forecast_confidence?: number;
}

export interface BatchScheduleRequest {
  start_date: string;
  end_date: string;
  job_ids?: string[];
  constraints?: Record<string, unknown>;
}

export interface BatchScheduleResponse {
  weeks: Array<{
    week_start: string;
    assignments: Array<{
      job_id: string;
      staff_id: string;
      scheduled_date: string;
    }>;
    utilization_pct: number;
  }>;
  total_jobs_scheduled: number;
  warnings: string[];
}

export interface UtilizationReport {
  period_start: string;
  period_end: string;
  resources: Array<{
    staff_id: string;
    staff_name: string;
    total_jobs: number;
    total_minutes: number;
    utilization_pct: number;
    revenue_per_hour: number;
  }>;
  overall_utilization_pct: number;
}

export interface CriteriaConfig {
  criterion_number: number;
  criterion_name: string;
  group: string;
  weight: number;
  is_hard: boolean;
  enabled: boolean;
}

// ---- Query key factory ----------------------------------------------------

export const aiSchedulingKeys = {
  all: ['ai-scheduling'] as const,
  capacityForecast: (date: string) =>
    [...aiSchedulingKeys.all, 'capacity-forecast', date] as const,
  utilization: (start: string, end: string) =>
    [...aiSchedulingKeys.all, 'utilization', start, end] as const,
  criteria: () => [...aiSchedulingKeys.all, 'criteria'] as const,
};

// ---- Hooks ----------------------------------------------------------------

/**
 * Extended capacity forecast with 30-criteria analysis.
 * Extends the existing useScheduleCapacity with additional AI fields.
 */
export function useCapacityForecast(date: string) {
  return useQuery({
    queryKey: aiSchedulingKeys.capacityForecast(date),
    queryFn: async () => {
      const response = await apiClient.get<CapacityForecastExtended>(
        `/schedule/capacity/${date}`
      );
      return response.data;
    },
    enabled: !!date,
  });
}

/**
 * Batch schedule generation for multi-week campaigns.
 */
export function useBatchGenerate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: BatchScheduleRequest) => {
      const response = await apiClient.post<BatchScheduleResponse>(
        '/schedule/batch-generate',
        request
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiSchedulingKeys.all });
      queryClient.invalidateQueries({ queryKey: ['appointments'] });
    },
  });
}

/**
 * Resource utilization report for a date range.
 */
export function useUtilizationReport(params: {
  start_date: string;
  end_date: string;
}) {
  return useQuery({
    queryKey: aiSchedulingKeys.utilization(params.start_date, params.end_date),
    queryFn: async () => {
      const response = await apiClient.get<UtilizationReport>(
        '/schedule/utilization',
        { params }
      );
      return response.data;
    },
    enabled: !!params.start_date && !!params.end_date,
  });
}

/**
 * Evaluate a schedule against all 30 criteria.
 */
export function useEvaluateSchedule() {
  return useMutation({
    mutationFn: async (schedule_date: string) => {
      const response = await apiClient.post<ScheduleEvaluation>(
        '/ai-scheduling/evaluate',
        { schedule_date }
      );
      return response.data;
    },
  });
}

/**
 * Fetch all 30 criteria configurations with current weights.
 */
export function useCriteriaConfig() {
  return useQuery({
    queryKey: aiSchedulingKeys.criteria(),
    queryFn: async () => {
      const response = await apiClient.get<CriteriaConfig[]>(
        '/ai-scheduling/criteria'
      );
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // criteria config rarely changes
  });
}
