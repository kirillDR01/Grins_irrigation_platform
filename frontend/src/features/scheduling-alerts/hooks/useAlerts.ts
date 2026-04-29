import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { alertsApi } from '../api/alertsApi';
import type { AlertsListParams } from '../types';

export const alertKeys = {
  all: ['scheduling-alerts'] as const,
  lists: () => [...alertKeys.all, 'list'] as const,
  list: (params?: AlertsListParams) =>
    [...alertKeys.lists(), params] as const,
  changeRequests: () => [...alertKeys.all, 'change-requests'] as const,
};

export function useAlerts(params?: AlertsListParams) {
  return useQuery({
    queryKey: alertKeys.list(params),
    queryFn: () => alertsApi.list(params),
    refetchInterval: 30_000,
  });
}

export function useResolveAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      action,
      parameters,
    }: {
      id: string;
      action: string;
      parameters?: Record<string, unknown>;
    }) => alertsApi.resolve(id, { action, parameters }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: alertKeys.lists() });
    },
  });
}

export function useDismissAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      alertsApi.dismiss(id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: alertKeys.lists() });
    },
  });
}

export function useChangeRequests() {
  return useQuery({
    queryKey: alertKeys.changeRequests(),
    queryFn: alertsApi.listChangeRequests,
    refetchInterval: 30_000,
  });
}

export function useApproveChangeRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      admin_notes,
    }: {
      id: string;
      admin_notes?: string;
    }) => alertsApi.approveChangeRequest(id, admin_notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: alertKeys.changeRequests() });
    },
  });
}

export function useDenyChangeRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      alertsApi.denyChangeRequest(id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: alertKeys.changeRequests() });
    },
  });
}
