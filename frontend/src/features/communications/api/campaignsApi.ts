/**
 * Campaign API client for the Communications feature.
 *
 * Validates: Requirement 22.6
 */

import { apiClient } from '@/core/api';
import type { PaginatedResponse } from '@/core/api';
import type {
  AudiencePreview,
  Campaign,
  CampaignCancelResult,
  CampaignCreate,
  CampaignRecipient,
  CampaignRetryResult,
  CampaignSendAccepted,
  CampaignStats,
  CsvUploadResult,
  TargetAudience,
  WorkerHealth,
} from '../types/campaign';

export interface ListCampaignsParams {
  page?: number;
  page_size?: number;
  status?: string;
}

export const campaignsApi = {
  create: async (data: CampaignCreate): Promise<Campaign> => {
    const response = await apiClient.post<Campaign>('/campaigns', data);
    return response.data;
  },

  list: async (
    params?: ListCampaignsParams,
  ): Promise<PaginatedResponse<Campaign>> => {
    const response = await apiClient.get<PaginatedResponse<Campaign>>(
      '/campaigns',
      { params },
    );
    return response.data;
  },

  get: async (id: string): Promise<Campaign> => {
    const response = await apiClient.get<Campaign>(`/campaigns/${id}`);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/campaigns/${id}`);
  },

  send: async (id: string): Promise<CampaignSendAccepted> => {
    const response = await apiClient.post<CampaignSendAccepted>(
      `/campaigns/${id}/send`,
    );
    return response.data;
  },

  cancel: async (id: string): Promise<CampaignCancelResult> => {
    const response = await apiClient.post<CampaignCancelResult>(
      `/campaigns/${id}/cancel`,
    );
    return response.data;
  },

  retryFailed: async (id: string): Promise<CampaignRetryResult> => {
    const response = await apiClient.post<CampaignRetryResult>(
      `/campaigns/${id}/retry-failed`,
    );
    return response.data;
  },

  getRecipients: async (
    id: string,
    params?: { page?: number; page_size?: number; status?: string },
  ): Promise<PaginatedResponse<CampaignRecipient>> => {
    const response = await apiClient.get<PaginatedResponse<CampaignRecipient>>(
      `/campaigns/${id}/recipients`,
      { params },
    );
    return response.data;
  },

  getStats: async (id: string): Promise<CampaignStats> => {
    const response = await apiClient.get<CampaignStats>(
      `/campaigns/${id}/stats`,
    );
    return response.data;
  },

  previewAudience: async (
    targetAudience: TargetAudience,
  ): Promise<AudiencePreview> => {
    const response = await apiClient.post<AudiencePreview>(
      '/campaigns/audience/preview',
      targetAudience,
    );
    return response.data;
  },

  uploadCsv: async (
    file: File,
    attestation: {
      staff_attestation_confirmed: boolean;
      attestation_text_shown: string;
      attestation_version: string;
    },
  ): Promise<CsvUploadResult> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append(
      'staff_attestation_confirmed',
      String(attestation.staff_attestation_confirmed),
    );
    formData.append('attestation_text_shown', attestation.attestation_text_shown);
    formData.append('attestation_version', attestation.attestation_version);

    const response = await apiClient.post<CsvUploadResult>(
      '/campaigns/audience/csv',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    );
    return response.data;
  },

  getWorkerHealth: async (): Promise<WorkerHealth> => {
    const response = await apiClient.get<WorkerHealth>(
      '/campaigns/worker-health',
    );
    return response.data;
  },
};
