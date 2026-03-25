import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { salesApi } from '../api/salesApi';
import type { MediaListParams, EstimateCreateRequest } from '../types';

// Query key factory
export const salesKeys = {
  all: ['sales'] as const,
  metrics: () => [...salesKeys.all, 'metrics'] as const,
  estimates: () => [...salesKeys.all, 'estimates'] as const,
  estimateList: (params?: Record<string, string>) => [...salesKeys.estimates(), params] as const,
  estimateDetail: (id: string) => [...salesKeys.estimates(), 'detail', id] as const,
  templates: () => [...salesKeys.all, 'templates'] as const,
  media: () => [...salesKeys.all, 'media'] as const,
  mediaList: (params?: MediaListParams) => [...salesKeys.media(), params] as const,
  followUps: () => [...salesKeys.all, 'follow-ups'] as const,
};

// Sales metrics
export function useSalesMetrics() {
  return useQuery({
    queryKey: salesKeys.metrics(),
    queryFn: () => salesApi.getMetrics(),
  });
}

// Estimate list
export function useEstimates(params?: Record<string, string>) {
  return useQuery({
    queryKey: salesKeys.estimateList(params),
    queryFn: () => salesApi.getEstimates(params),
  });
}

// Estimate templates
export function useEstimateTemplates() {
  return useQuery({
    queryKey: salesKeys.templates(),
    queryFn: () => salesApi.getTemplates(),
  });
}

// Create estimate mutation
export function useCreateEstimate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: EstimateCreateRequest) => salesApi.createEstimate(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: salesKeys.estimates() });
      qc.invalidateQueries({ queryKey: salesKeys.metrics() });
    },
  });
}

// Send estimate mutation
export function useSendEstimate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => salesApi.sendEstimate(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: salesKeys.estimates() });
      qc.invalidateQueries({ queryKey: salesKeys.metrics() });
    },
  });
}

// Media library
export function useMedia(params?: MediaListParams) {
  return useQuery({
    queryKey: salesKeys.mediaList(params),
    queryFn: () => salesApi.getMedia(params),
  });
}

// Upload media mutation
export function useUploadMedia() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ file, metadata }: { file: File; metadata: { category: string; media_type: string; caption?: string } }) =>
      salesApi.uploadMedia(file, metadata),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: salesKeys.media() });
    },
  });
}

// Follow-up queue
export function useFollowUps() {
  return useQuery({
    queryKey: salesKeys.followUps(),
    queryFn: () => salesApi.getFollowUps(),
  });
}

// Estimate detail (Req 83)
export function useEstimateDetail(id: string) {
  return useQuery({
    queryKey: salesKeys.estimateDetail(id),
    queryFn: () => salesApi.getEstimateDetail(id),
    enabled: !!id,
  });
}

// Cancel estimate mutation
export function useCancelEstimate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => salesApi.cancelEstimate(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: salesKeys.estimates() });
      qc.invalidateQueries({ queryKey: salesKeys.metrics() });
    },
  });
}

// Create job from estimate mutation
export function useCreateJobFromEstimate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => salesApi.createJobFromEstimate(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: salesKeys.estimates() });
      qc.invalidateQueries({ queryKey: salesKeys.metrics() });
    },
  });
}
