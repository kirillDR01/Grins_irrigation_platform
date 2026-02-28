import { apiClient } from '@/core/api';
import type {
  Lead,
  LeadListParams,
  LeadUpdate,
  LeadConversionRequest,
  LeadConversionResponse,
  PaginatedLeadResponse,
} from '../types';

const BASE_PATH = '/leads';

export const leadApi = {
  // List leads with pagination and filters
  list: async (params?: LeadListParams): Promise<PaginatedLeadResponse> => {
    const response = await apiClient.get<PaginatedLeadResponse>(BASE_PATH, {
      params,
    });
    return response.data;
  },

  // Get single lead by ID
  getById: async (id: string): Promise<Lead> => {
    const response = await apiClient.get<Lead>(`${BASE_PATH}/${id}`);
    return response.data;
  },

  // Update lead (status, assignment, notes)
  update: async (id: string, data: LeadUpdate): Promise<Lead> => {
    const response = await apiClient.patch<Lead>(`${BASE_PATH}/${id}`, data);
    return response.data;
  },

  // Convert lead to customer (and optionally a job)
  convert: async (id: string, data: LeadConversionRequest): Promise<LeadConversionResponse> => {
    const response = await apiClient.post<LeadConversionResponse>(
      `${BASE_PATH}/${id}/convert`,
      data
    );
    return response.data;
  },

  // Delete lead
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`${BASE_PATH}/${id}`);
  },
};
