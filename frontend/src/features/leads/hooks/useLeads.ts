import { useQuery } from '@tanstack/react-query';
import { leadApi } from '../api/leadApi';
import type { LeadListParams, LeadMetricsBySourceParams } from '../types';

// Query key factory
export const leadKeys = {
  all: ['leads'] as const,
  lists: () => [...leadKeys.all, 'list'] as const,
  list: (params?: LeadListParams) => [...leadKeys.lists(), params] as const,
  details: () => [...leadKeys.all, 'detail'] as const,
  detail: (id: string) => [...leadKeys.details(), id] as const,
  followUpQueue: () => [...leadKeys.all, 'follow-up-queue'] as const,
  metricsBySource: (params?: LeadMetricsBySourceParams) => [...leadKeys.all, 'metrics-by-source', params] as const,
};

// List leads with pagination and filters
export function useLeads(params?: LeadListParams) {
  return useQuery({
    queryKey: leadKeys.list(params),
    queryFn: () => leadApi.list(params),
  });
}

// Get single lead by ID
export function useLead(id: string) {
  return useQuery({
    queryKey: leadKeys.detail(id),
    queryFn: () => leadApi.getById(id),
    enabled: !!id,
  });
}

// Follow-up queue
export function useFollowUpQueue() {
  return useQuery({
    queryKey: leadKeys.followUpQueue(),
    queryFn: () => leadApi.followUpQueue(),
  });
}

// Lead metrics grouped by source
export function useLeadMetricsBySource(params?: LeadMetricsBySourceParams) {
  return useQuery({
    queryKey: leadKeys.metricsBySource(params),
    queryFn: () => leadApi.metricsBySource(params),
  });
}
