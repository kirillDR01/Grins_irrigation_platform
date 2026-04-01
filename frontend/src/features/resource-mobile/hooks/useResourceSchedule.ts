/**
 * TanStack Query hooks for resource mobile data.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { resourceApi } from '../api/resourceApi';
import type {
  ResourceScheduleParams,
  ResourceAlertsParams,
  ResourceSuggestionsParams,
} from '../types';

// ── Query key factory ──────────────────────────────────────────────────

export const resourceKeys = {
  all: ['resource-mobile'] as const,
  schedule: (params?: ResourceScheduleParams) =>
    [...resourceKeys.all, 'schedule', params] as const,
  alerts: (params?: ResourceAlertsParams) =>
    [...resourceKeys.all, 'alerts', params] as const,
  suggestions: (params?: ResourceSuggestionsParams) =>
    [...resourceKeys.all, 'suggestions', params] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────

/** Fetch the resource's day schedule. */
export function useResourceSchedule(params?: ResourceScheduleParams) {
  return useQuery({
    queryKey: resourceKeys.schedule(params),
    queryFn: () => resourceApi.getSchedule(params),
  });
}

/** Fetch resource-facing alerts with polling. */
export function useResourceAlerts(
  params?: ResourceAlertsParams,
  refetchInterval = 30_000
) {
  return useQuery({
    queryKey: resourceKeys.alerts(params),
    queryFn: () => resourceApi.getAlerts(params),
    refetchInterval,
  });
}

/** Mark a resource alert as read. */
export function useMarkAlertRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => resourceApi.markAlertRead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...resourceKeys.all, 'alerts'] });
    },
  });
}

/** Fetch resource-facing suggestions. */
export function useResourceSuggestions(
  params?: ResourceSuggestionsParams,
  refetchInterval = 60_000
) {
  return useQuery({
    queryKey: resourceKeys.suggestions(params),
    queryFn: () => resourceApi.getSuggestions(params),
    refetchInterval,
  });
}

/** Dismiss a resource suggestion. */
export function useDismissResourceSuggestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => resourceApi.dismissSuggestion(id),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: [...resourceKeys.all, 'suggestions'],
      });
    },
  });
}
