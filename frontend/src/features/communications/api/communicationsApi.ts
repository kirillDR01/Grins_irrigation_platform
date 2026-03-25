import { apiClient } from '@/core/api';
import type { PaginatedResponse } from '@/core/api';
import type {
  Communication,
  SentMessage,
  SentMessageListParams,
  UnaddressedCountResponse,
} from '../types';

export const communicationsApi = {
  // Get unaddressed inbound communications
  getUnaddressed: async (): Promise<PaginatedResponse<Communication>> => {
    const response = await apiClient.get<PaginatedResponse<Communication>>(
      '/communications',
      { params: { addressed: 'false' } },
    );
    return response.data;
  },

  // Mark a communication as addressed
  markAddressed: async (id: string): Promise<void> => {
    await apiClient.patch(`/communications/${id}/address`);
  },

  // Get unaddressed count
  getUnaddressedCount: async (): Promise<UnaddressedCountResponse> => {
    const response = await apiClient.get<UnaddressedCountResponse>(
      '/communications/unaddressed-count',
    );
    return response.data;
  },

  // Get sent messages (outbound notifications) with filters
  getSentMessages: async (
    params?: SentMessageListParams,
  ): Promise<PaginatedResponse<SentMessage>> => {
    const response = await apiClient.get<PaginatedResponse<SentMessage>>(
      '/sent-messages',
      { params },
    );
    return response.data;
  },
};
