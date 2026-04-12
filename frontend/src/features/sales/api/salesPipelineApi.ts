import { apiClient } from '@/core/api';
import type {
  SalesEntry,
  SalesPipelineListResponse,
  SalesEntryStatusUpdate,
} from '../types/pipeline';

export const salesPipelineApi = {
  list: async (params?: {
    skip?: number;
    limit?: number;
    status?: string;
  }): Promise<SalesPipelineListResponse> => {
    const response = await apiClient.get<SalesPipelineListResponse>(
      '/sales/pipeline',
      { params },
    );
    return response.data;
  },

  get: async (id: string): Promise<SalesEntry> => {
    const response = await apiClient.get<SalesEntry>(`/sales/pipeline/${id}`);
    return response.data;
  },

  advance: async (id: string): Promise<SalesEntry> => {
    const response = await apiClient.post<SalesEntry>(
      `/sales/pipeline/${id}/advance`,
    );
    return response.data;
  },

  overrideStatus: async (
    id: string,
    body: SalesEntryStatusUpdate,
  ): Promise<SalesEntry> => {
    const response = await apiClient.put<SalesEntry>(
      `/sales/pipeline/${id}/status`,
      body,
    );
    return response.data;
  },

  convert: async (id: string): Promise<{ job_id: string }> => {
    const response = await apiClient.post<{ job_id: string }>(
      `/sales/pipeline/${id}/convert`,
    );
    return response.data;
  },

  forceConvert: async (
    id: string,
  ): Promise<{ job_id: string; forced: boolean }> => {
    const response = await apiClient.post<{
      job_id: string;
      forced: boolean;
    }>(`/sales/pipeline/${id}/force-convert`);
    return response.data;
  },

  markLost: async (
    id: string,
    closedReason?: string,
  ): Promise<SalesEntry> => {
    const response = await apiClient.delete<SalesEntry>(
      `/sales/pipeline/${id}`,
      { params: closedReason ? { closed_reason: closedReason } : undefined },
    );
    return response.data;
  },
};
