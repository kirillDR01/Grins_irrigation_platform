import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workRequestApi } from '../api/workRequestApi';
import type { WorkRequestListParams } from '../types';

// Query key factory
export const workRequestKeys = {
  all: ['work-requests'] as const,
  lists: () => [...workRequestKeys.all, 'list'] as const,
  list: (params?: WorkRequestListParams) => [...workRequestKeys.lists(), params] as const,
  details: () => [...workRequestKeys.all, 'detail'] as const,
  detail: (id: string) => [...workRequestKeys.details(), id] as const,
  syncStatus: () => [...workRequestKeys.all, 'sync-status'] as const,
};

export function useWorkRequests(params?: WorkRequestListParams) {
  return useQuery({
    queryKey: workRequestKeys.list(params),
    queryFn: () => workRequestApi.list(params),
  });
}

export function useWorkRequest(id: string) {
  return useQuery({
    queryKey: workRequestKeys.detail(id),
    queryFn: () => workRequestApi.getById(id),
    enabled: !!id,
  });
}

export function useSyncStatus() {
  return useQuery({
    queryKey: workRequestKeys.syncStatus(),
    queryFn: () => workRequestApi.getSyncStatus(),
    refetchInterval: 30_000,
  });
}

export function useCreateLeadFromSubmission() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => workRequestApi.createLead(id),
    onSuccess: (updatedRequest) => {
      queryClient.setQueryData(workRequestKeys.detail(updatedRequest.id), updatedRequest);
      queryClient.invalidateQueries({ queryKey: workRequestKeys.lists() });
    },
  });
}

export function useTriggerSync() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => workRequestApi.triggerSync(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workRequestKeys.lists() });
      queryClient.invalidateQueries({ queryKey: workRequestKeys.syncStatus() });
    },
  });
}
