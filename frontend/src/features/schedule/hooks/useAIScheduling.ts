/**
 * TanStack Query hooks for AI scheduling extensions.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/core/api/client';

// ── Types ──────────────────────────────────────────────────────────────

export interface CapacityForecastParams {
  start_date?: string;
  end_date?: string;
  job_type?: string;
  zone_id?: string;
}

export interface CapacityForecast {
  weeks: {
    week_start: string;
    available_hours: number;
    booked_hours: number;
    utilization_pct: number;
    open_slots: number;
  }[];
}

export interface BatchScheduleRequest {
  job_type: string;
  customer_count: number;
  weeks: number;
  zone_priority?: string[];
  overtime_approved?: boolean;
}

export interface BatchScheduleResponse {
  weeks: {
    week_start: string;
    jobs: { job_id: string; staff_id: string; date: string; zone: string }[];
    utilization_pct: number;
  }[];
  total_jobs_scheduled: number;
  notifications_ready: number;
}

export interface UtilizationReportParams {
  start_date?: string;
  end_date?: string;
}

export interface UtilizationReport {
  resources: {
    staff_id: string;
    name: string;
    utilization_pct: number;
    job_hours: number;
    drive_hours: number;
    available_hours: number;
  }[];
  average_utilization: number;
}

export interface ScheduleEvaluationRequest {
  schedule_date: string;
}

export interface CriteriaScoreItem {
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
  criteria_scores: CriteriaScoreItem[];
  alerts: unknown[];
}

export interface CriteriaConfigItem {
  id: string;
  criterion_number: number;
  criterion_name: string;
  criterion_group: string;
  weight: number;
  is_hard_constraint: boolean;
  is_enabled: boolean;
}

// ── Query key factory ──────────────────────────────────────────────────

export const aiSchedulingKeys = {
  all: ['ai-scheduling'] as const,
  capacityForecast: (params?: CapacityForecastParams) =>
    [...aiSchedulingKeys.all, 'capacity-forecast', params] as const,
  utilization: (params?: UtilizationReportParams) =>
    [...aiSchedulingKeys.all, 'utilization', params] as const,
  criteria: () => [...aiSchedulingKeys.all, 'criteria'] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────

/** GET /api/v1/schedule/capacity-forecast */
export function useCapacityForecast(params?: CapacityForecastParams) {
  return useQuery({
    queryKey: aiSchedulingKeys.capacityForecast(params),
    queryFn: async () => {
      const response = await apiClient.get<CapacityForecast>(
        '/schedule/capacity-forecast',
        { params }
      );
      return response.data;
    },
  });
}

/** POST /api/v1/schedule/batch-generate */
export function useBatchGenerate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (request: BatchScheduleRequest) => {
      const response = await apiClient.post<BatchScheduleResponse>(
        '/schedule/batch-generate',
        request
      );
      return response.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: aiSchedulingKeys.all });
      qc.invalidateQueries({ queryKey: ['appointments'] });
    },
  });
}

/** GET /api/v1/schedule/utilization */
export function useUtilizationReport(params?: UtilizationReportParams) {
  return useQuery({
    queryKey: aiSchedulingKeys.utilization(params),
    queryFn: async () => {
      const response = await apiClient.get<UtilizationReport>(
        '/schedule/utilization',
        { params }
      );
      return response.data;
    },
  });
}

/** POST /api/v1/ai-scheduling/evaluate */
export function useEvaluateSchedule() {
  return useMutation({
    mutationFn: async (request: ScheduleEvaluationRequest) => {
      const response = await apiClient.post<ScheduleEvaluation>(
        '/ai-scheduling/evaluate',
        request
      );
      return response.data;
    },
  });
}

/** GET /api/v1/ai-scheduling/criteria */
export function useCriteriaConfig() {
  return useQuery({
    queryKey: aiSchedulingKeys.criteria(),
    queryFn: async () => {
      const response = await apiClient.get<CriteriaConfigItem[]>(
        '/ai-scheduling/criteria'
      );
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // criteria config rarely changes
  });
}
