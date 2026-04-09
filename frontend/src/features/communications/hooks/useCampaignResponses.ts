/**
 * React Query hooks for campaign poll response endpoints.
 *
 * Validates: Scheduling Poll Req 9.1, 10.1
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/core/api';
import type { PaginatedResponse } from '@/core/api';
import type {
  CampaignResponseRow,
  CampaignResponseSummary,
} from '../types/campaign';

// --- Query key factory ---

export interface CampaignResponseListParams {
  option_key?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export const campaignResponseKeys = {
  all: (campaignId: string) => ['campaigns', campaignId, 'responses'] as const,
  summary: (campaignId: string) =>
    [...campaignResponseKeys.all(campaignId), 'summary'] as const,
  lists: (campaignId: string) =>
    [...campaignResponseKeys.all(campaignId), 'list'] as const,
  list: (campaignId: string, params?: CampaignResponseListParams) =>
    [...campaignResponseKeys.lists(campaignId), params] as const,
};

// --- API calls ---

async function fetchResponseSummary(
  campaignId: string,
): Promise<CampaignResponseSummary> {
  const res = await apiClient.get<CampaignResponseSummary>(
    `/campaigns/${campaignId}/responses/summary`,
  );
  return res.data;
}

async function fetchResponses(
  campaignId: string,
  params?: CampaignResponseListParams,
): Promise<PaginatedResponse<CampaignResponseRow>> {
  const res = await apiClient.get<PaginatedResponse<CampaignResponseRow>>(
    `/campaigns/${campaignId}/responses`,
    { params },
  );
  return res.data;
}

// --- Hooks ---

export function useCampaignResponseSummary(campaignId: string) {
  return useQuery({
    queryKey: campaignResponseKeys.summary(campaignId),
    queryFn: () => fetchResponseSummary(campaignId),
    enabled: !!campaignId,
  });
}

export function useCampaignResponses(
  campaignId: string,
  params?: CampaignResponseListParams,
) {
  return useQuery({
    queryKey: campaignResponseKeys.list(campaignId, params),
    queryFn: () => fetchResponses(campaignId, params),
    enabled: !!campaignId,
  });
}
