import { apiClient } from '@/core/api';
import type { PaginatedResponse } from '@/core/api';
import type {
  ServiceOffering,
  ServiceOfferingCreate,
  ServiceOfferingHistory,
  ServiceOfferingListParams,
  ServiceOfferingUpdate,
} from '../types';

const BASE_PATH = '/services';

export const serviceApi = {
  list: async (
    params?: ServiceOfferingListParams,
  ): Promise<PaginatedResponse<ServiceOffering>> => {
    const response = await apiClient.get<PaginatedResponse<ServiceOffering>>(
      BASE_PATH,
      { params },
    );
    return response.data;
  },

  get: async (id: string): Promise<ServiceOffering> => {
    const response = await apiClient.get<ServiceOffering>(`${BASE_PATH}/${id}`);
    return response.data;
  },

  create: async (data: ServiceOfferingCreate): Promise<ServiceOffering> => {
    const response = await apiClient.post<ServiceOffering>(BASE_PATH, data);
    return response.data;
  },

  // Phase 2 ships with plain UPDATE. Phase 1.5 swaps the backend for
  // archive+create without a frontend signature change.
  update: async (
    id: string,
    data: ServiceOfferingUpdate,
  ): Promise<ServiceOffering> => {
    const response = await apiClient.put<ServiceOffering>(`${BASE_PATH}/${id}`, data);
    return response.data;
  },

  // Soft-delete via the existing /api/v1/services DELETE.
  deactivate: async (id: string): Promise<void> => {
    await apiClient.delete(`${BASE_PATH}/${id}`);
  },

  // Phase 2 placeholder — backend archive history endpoint lands in
  // Phase 1.5. Keep the surface so the sheet wires now and lights up later.
  history: async (id: string): Promise<ServiceOfferingHistory> => {
    try {
      const response = await apiClient.get<ServiceOfferingHistory>(
        `${BASE_PATH}/${id}/history`,
      );
      return response.data;
    } catch {
      return [];
    }
  },

  // Auto-generated pricelist.md (Phase 2 / P8). Returns plain markdown.
  exportMarkdown: async (): Promise<string> => {
    const response = await apiClient.get<string>(
      `${BASE_PATH}/export/pricelist.md`,
      { responseType: 'text', transformResponse: (v) => v as string },
    );
    return response.data;
  },
};
