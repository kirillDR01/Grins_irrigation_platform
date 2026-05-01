/**
 * Fan out 7 per-day capacity-forecast queries via TanStack `useQueries`.
 *
 * Mirrors `useWeeklyUtilization` — reuses `aiSchedulingKeys.capacityForecast(date)`
 * so cache entries are shared with `useCapacityForecast(date)` callers.
 */

import { useQueries } from '@tanstack/react-query';
import { addDays, format } from 'date-fns';
import { apiClient } from '@/core/api/client';
import {
  aiSchedulingKeys,
  type CapacityForecastExtended,
} from './useAIScheduling';

export interface WeeklyCapacityResult {
  /** One CapacityForecastExtended per day, indexed by `addDays(weekStart, i)`. */
  days: Array<CapacityForecastExtended | undefined>;
  isLoading: boolean;
  isError: boolean;
}

export function useWeeklyCapacity(weekStart: Date): WeeklyCapacityResult {
  const dates = Array.from({ length: 7 }, (_, i) =>
    format(addDays(weekStart, i), 'yyyy-MM-dd')
  );

  const queries = useQueries({
    queries: dates.map((date) => ({
      queryKey: aiSchedulingKeys.capacityForecast(date),
      queryFn: async () => {
        const res = await apiClient.get<CapacityForecastExtended>(
          `/schedule/capacity/${date}`
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
