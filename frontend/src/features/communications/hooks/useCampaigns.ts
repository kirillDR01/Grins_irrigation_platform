import { useQuery } from '@tanstack/react-query';
import { campaignsApi } from '../api/campaignsApi';
import type { ListCampaignsParams } from '../api/campaignsApi';

/** Query key factory for campaigns */
export const campaignKeys = {
  all: ['campaigns'] as const,
  lists: () => [...campaignKeys.all, 'list'] as const,
  list: (params?: ListCampaignsParams) =>
    [...campaignKeys.lists(), params] as const,
  details: () => [...campaignKeys.all, 'detail'] as const,
  detail: (id: string) => [...campaignKeys.details(), id] as const,
  stats: (id: string) => [...campaignKeys.all, id, 'stats'] as const,
  recipients: (id: string, params?: Record<string, unknown>) =>
    [...campaignKeys.all, id, 'recipients', params] as const,
  audiencePreview: () => [...campaignKeys.all, 'audience-preview'] as const,
  workerHealth: () => [...campaignKeys.all, 'worker-health'] as const,
};

/** List campaigns with pagination and optional status filter */
export function useCampaigns(params?: ListCampaignsParams) {
  return useQuery({
    queryKey: campaignKeys.list(params),
    queryFn: () => campaignsApi.list(params),
  });
}

/** Get a single campaign by ID */
export function useCampaign(id: string) {
  return useQuery({
    queryKey: campaignKeys.detail(id),
    queryFn: () => campaignsApi.get(id),
    enabled: !!id,
  });
}

/** Get campaign stats (recipient breakdown) */
export function useCampaignStats(id: string) {
  return useQuery({
    queryKey: campaignKeys.stats(id),
    queryFn: () => campaignsApi.getStats(id),
    enabled: !!id,
  });
}

/** List campaign recipients with optional status filter */
export function useCampaignRecipients(
  id: string,
  params?: { page?: number; page_size?: number; status?: string },
) {
  return useQuery({
    queryKey: campaignKeys.recipients(id, params),
    queryFn: () => campaignsApi.getRecipients(id, params),
    enabled: !!id,
  });
}
