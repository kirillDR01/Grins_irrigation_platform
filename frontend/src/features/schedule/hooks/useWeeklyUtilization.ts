/**
 * Fan out 7 per-day utilization queries via TanStack `useQueries`.
 *
 * Reuses `aiSchedulingKeys.utilization(date)` so cache entries are
 * shared with `useUtilizationReport(date)` consumers — no double-fetch
 * when both the resource-timeline and the AI scheduling overview are
 * mounted on the same page.
 */

import { useQueries } from '@tanstack/react-query';
import { addDays, format } from 'date-fns';
import { apiClient } from '@/core/api/client';
import { aiSchedulingKeys, type UtilizationReport } from './useAIScheduling';

export interface WeeklyUtilizationResult {
  /** One UtilizationReport per day, indexed by `addDays(weekStart, i)`. */
  days: Array<UtilizationReport | undefined>;
  isLoading: boolean;
  isError: boolean;
}

export function useWeeklyUtilization(weekStart: Date): WeeklyUtilizationResult {
  const dates = Array.from({ length: 7 }, (_, i) =>
    format(addDays(weekStart, i), 'yyyy-MM-dd')
  );

  const queries = useQueries({
    queries: dates.map((date) => ({
      queryKey: aiSchedulingKeys.utilization(date),
      queryFn: async () => {
        const res = await apiClient.get<UtilizationReport>(
          '/schedule/utilization',
          { params: { schedule_date: date } }
        );
        return res.data;
      },
      staleTime: 30_000,
    })),
  });

  return {
    days: queries.map((q) => q.data),
    isLoading: queries.some((q) => q.isLoading),
    isError: queries.some((q) => q.isError),
  };
}
