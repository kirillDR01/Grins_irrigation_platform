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
      // Build staff assignment summaries from results matching backend schema
      const staff_assignments: StaffAssignmentSummary[] = results.assignments.map((assignment) => {
        const jobs = assignment.jobs || [];
        
        // Extract unique cities and job types from jobs
        const cities = [...new Set(jobs.map(job => job.city).filter((c): c is string => c !== null))];
        const job_types = [...new Set(jobs.map(job => job.service_type))];
        
        // Calculate total minutes from job durations
        const total_minutes = jobs.reduce((sum, job) => sum + job.duration_minutes, 0);

        return {
          staff_id: assignment.staff_id,
          staff_name: assignment.staff_name,
          job_count: jobs.length,
          total_minutes,
          cities,
          job_types,
        };
      });

      const response = await scheduleGenerationApi.explainSchedule({
        schedule_date: scheduleDate,
        staff_assignments,
        unassigned_job_count: results.unassigned_jobs?.length || 0,
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
