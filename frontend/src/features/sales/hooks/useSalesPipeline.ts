import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { salesPipelineApi } from '../api/salesPipelineApi';
import type { SalesEntryStatusUpdate } from '../types/pipeline';

export const pipelineKeys = {
  all: ['sales-pipeline'] as const,
  lists: () => [...pipelineKeys.all, 'list'] as const,
  list: (params?: { skip?: number; limit?: number; status?: string }) =>
    [...pipelineKeys.lists(), params] as const,
  detail: (id: string) => [...pipelineKeys.all, 'detail', id] as const,
};

export function useSalesPipeline(params?: {
  skip?: number;
  limit?: number;
  status?: string;
}) {
  return useQuery({
    queryKey: pipelineKeys.list(params),
    queryFn: () => salesPipelineApi.list(params),
  });
}

export function useSalesEntry(id: string) {
  return useQuery({
    queryKey: pipelineKeys.detail(id),
    queryFn: () => salesPipelineApi.get(id),
    enabled: !!id,
  });
}

export function useAdvanceSalesEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => salesPipelineApi.advance(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}

export function useOverrideSalesStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: SalesEntryStatusUpdate }) =>
      salesPipelineApi.overrideStatus(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}

export function useConvertToJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => salesPipelineApi.convert(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}

export function useForceConvertToJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => salesPipelineApi.forceConvert(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}

export function useMarkSalesLost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      closedReason,
    }: {
      id: string;
      closedReason?: string;
    }) => salesPipelineApi.markLost(id, closedReason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}
