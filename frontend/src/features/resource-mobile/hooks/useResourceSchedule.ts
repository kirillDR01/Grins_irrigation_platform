import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { resourceApi } from '../api/resourceApi';

export const resourceKeys = {
  all: ['resource-mobile'] as const,
  schedule: (staffId: string, date: string) =>
    [...resourceKeys.all, 'schedule', staffId, date] as const,
  alerts: (staffId: string) =>
    [...resourceKeys.all, 'alerts', staffId] as const,
  suggestions: (staffId: string) =>
    [...resourceKeys.all, 'suggestions', staffId] as const,
};

export function useResourceSchedule(staffId: string, date: string) {
  return useQuery({
    queryKey: resourceKeys.schedule(staffId, date),
    queryFn: () => resourceApi.getSchedule(staffId, date),
    enabled: Boolean(staffId && date),
  });
}

export function useResourceAlerts(staffId: string) {
  return useQuery({
    queryKey: resourceKeys.alerts(staffId),
    queryFn: () => resourceApi.getAlerts(staffId),
    enabled: Boolean(staffId),
    refetchInterval: 30_000,
  });
}

export function useResourceSuggestions(staffId: string) {
  return useQuery({
    queryKey: resourceKeys.suggestions(staffId),
    queryFn: () => resourceApi.getSuggestions(staffId),
    enabled: Boolean(staffId),
    refetchInterval: 30_000,
  });
}

export function useDismissResourceAlert(staffId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (alertId: string) => resourceApi.dismissAlert(staffId, alertId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: resourceKeys.alerts(staffId) });
    },
  });
}

export function useAcceptResourceSuggestion(staffId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (suggestionId: string) =>
      resourceApi.acceptSuggestion(staffId, suggestionId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: resourceKeys.suggestions(staffId) });
    },
  });
}
