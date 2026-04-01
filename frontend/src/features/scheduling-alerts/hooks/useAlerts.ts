/**
 * TanStack Query hooks for scheduling alerts.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { alertsApi } from '../api/alertsApi';
import type {
  AlertListParams,
  ResolveAlertRequest,
  DismissAlertRequest,
  ApproveChangeRequestPayload,
  DenyChangeRequestPayload,
} from '../types';

/** Query key factory for alerts. */
export const alertKeys = {
  all: ['scheduling-alerts'] as const,
  lists: () => [...alertKeys.all, 'list'] as const,
  list: (params?: AlertListParams) => [...alertKeys.lists(), params] as const,
  changeRequests: () => [...alertKeys.all, 'change-requests'] as const,
};

/**
 * Fetch active alerts/suggestions with polling.
 * Default refetch interval: 30 seconds.
 */
export function useAlerts(params?: AlertListParams, refetchInterval = 30_000) {
  return useQuery({
    queryKey: alertKeys.list(params),
    queryFn: () => alertsApi.list(params),
    refetchInterval,
  });
}

/** Resolve an alert with a chosen action. */
export function useResolveAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ResolveAlertRequest }) =>
      alertsApi.resolve(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: alertKeys.lists() });
    },
  });
}

/** Dismiss a suggestion. */
export function useDismissAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data?: DismissAlertRequest }) =>
      alertsApi.dismiss(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: alertKeys.lists() });
    },
  });
}

/** Fetch pending change requests. */
export function useChangeRequests() {
  return useQuery({
    queryKey: alertKeys.changeRequests(),
    queryFn: () => alertsApi.listChangeRequests(),
  });
}

/** Approve a change request. */
export function useApproveChangeRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data?: ApproveChangeRequestPayload;
    }) => alertsApi.approveChangeRequest(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: alertKeys.changeRequests() });
      qc.invalidateQueries({ queryKey: alertKeys.lists() });
    },
  });
}

/** Deny a change request. */
export function useDenyChangeRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: DenyChangeRequestPayload;
    }) => alertsApi.denyChangeRequest(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: alertKeys.changeRequests() });
      qc.invalidateQueries({ queryKey: alertKeys.lists() });
    },
  });
}
