/**
 * Hook for fetching schedule explanations.
 * Manages explanation fetch state and error handling.
 */

import { useState } from 'react';
import { scheduleGenerationApi } from '../api/scheduleGenerationApi';
import type {
  ScheduleGenerateResponse,
  ScheduleExplanationResponse,
  StaffAssignmentSummary,
} from '../types';

interface UseScheduleExplanationReturn {
  explanation: ScheduleExplanationResponse | null;
  isLoading: boolean;
  error: string | null;
  fetchExplanation: (
    results: ScheduleGenerateResponse,
    scheduleDate: string
  ) => Promise<void>;
}

export function useScheduleExplanation(): UseScheduleExplanationReturn {
  const [explanation, setExplanation] = useState<ScheduleExplanationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchExplanation = async (
    results: ScheduleGenerateResponse,
    scheduleDate: string
  ) => {
    setIsLoading(true);
    setError(null);

    try {
      // Build staff assignment summaries from results
      const assignments: StaffAssignmentSummary[] = results.assignments.map((assignment) => {
        const jobs = assignment.jobs || [];
        const firstJob = jobs[0];
        const lastJob = jobs[jobs.length - 1];

        return {
          staff_name: assignment.staff_name,
          total_jobs: jobs.length,
          total_travel_minutes: assignment.total_travel_minutes || 0,
          first_job_start: firstJob?.time_window_start || null,
          last_job_end: lastJob?.time_window_end || null,
        };
      });

      const response = await scheduleGenerationApi.explainSchedule({
        schedule_date: scheduleDate,
        assignments,
        unassigned_count: results.unassigned_jobs?.length || 0,
        total_travel_minutes: results.total_travel_minutes || 0,
      });

      setExplanation(response);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch explanation';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    explanation,
    isLoading,
    error,
    fetchExplanation,
  };
}
