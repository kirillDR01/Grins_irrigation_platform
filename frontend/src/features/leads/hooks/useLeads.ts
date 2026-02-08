import { useQuery } from '@tanstack/react-query';
import { leadApi } from '../api/leadApi';
import type { LeadListParams } from '../types';

// Query key factory
export const leadKeys = {
  all: ['leads'] as const,
  lists: () => [...leadKeys.all, 'list'] as const,
  list: (params?: LeadListParams) => [...leadKeys.lists(), params] as const,
  details: () => [...leadKeys.all, 'detail'] as const,
  detail: (id: string) => [...leadKeys.details(), id] as const,
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
