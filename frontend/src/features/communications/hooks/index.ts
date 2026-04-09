import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { communicationsApi } from '../api/communicationsApi';
import type { SentMessageListParams } from '../types';

// Query key factory
export const communicationsKeys = {
  all: ['communications'] as const,
  unaddressed: () => [...communicationsKeys.all, 'unaddressed'] as const,
  unaddressedCount: () => [...communicationsKeys.all, 'unaddressed-count'] as const,
  sentMessages: () => [...communicationsKeys.all, 'sent-messages'] as const,
  sentMessageList: (params?: SentMessageListParams) =>
    [...communicationsKeys.sentMessages(), params] as const,
};

// Unaddressed inbound communications
export function useUnaddressedCommunications() {
  return useQuery({
    queryKey: communicationsKeys.unaddressed(),
    queryFn: () => communicationsApi.getUnaddressed(),
  });
}

// Unaddressed count (for dashboard widget)
export function useUnaddressedCount() {
  return useQuery({
    queryKey: communicationsKeys.unaddressedCount(),
    queryFn: () => communicationsApi.getUnaddressedCount(),
  });
}

// Mark communication as addressed
export function useMarkAddressed() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => communicationsApi.markAddressed(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: communicationsKeys.unaddressed() });
      qc.invalidateQueries({ queryKey: communicationsKeys.unaddressedCount() });
    },
  });
}

// Sent messages (outbound notifications) with filters
export function useSentMessages(params?: SentMessageListParams) {
  return useQuery({
    queryKey: communicationsKeys.sentMessageList(params),
    queryFn: () => communicationsApi.getSentMessages(params),
  });
}

// Campaign hooks (CallRail SMS Integration)
export { campaignKeys, useCampaigns, useCampaign, useCampaignStats, useCampaignRecipients } from './useCampaigns';
export { useCreateCampaign, useUpdateCampaign, useDeleteCampaign } from './useCreateCampaign';
export { useSendCampaign, useCancelCampaign, useRetryFailed } from './useSendCampaign';
export { useAudiencePreview } from './useAudiencePreview';
export { useAudienceCsv } from './useAudienceCsv';
export { useCampaignProgress, useWorkerHealth } from './useCampaignProgress';
export { campaignResponseKeys, useCampaignResponseSummary, useCampaignResponses } from './useCampaignResponses';
export type { CampaignResponseListParams } from './useCampaignResponses';
