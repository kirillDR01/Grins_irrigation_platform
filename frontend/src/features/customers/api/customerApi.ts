import { apiClient } from '@/core/api';
import type { PaginatedResponse } from '@/core/api';
import type { Customer, CustomerCreate, CustomerUpdate, CustomerListParams } from '../types';

const BASE_PATH = '/customers';

export const customerApi = {
  // List customers with pagination and filters
  list: async (params?: CustomerListParams): Promise<PaginatedResponse<Customer>> => {
    const response = await apiClient.get<PaginatedResponse<Customer>>(BASE_PATH, {
      params,
    });
    return response.data;
  },

  // Get single customer by ID
  get: async (id: string): Promise<Customer> => {
    const response = await apiClient.get<Customer>(`${BASE_PATH}/${id}`);
    return response.data;
  },

  // Create new customer
  create: async (data: CustomerCreate): Promise<Customer> => {
    const response = await apiClient.post<Customer>(BASE_PATH, data);
    return response.data;
  },

  // Update existing customer
  update: async (id: string, data: CustomerUpdate): Promise<Customer> => {
    const response = await apiClient.put<Customer>(`${BASE_PATH}/${id}`, data);
    return response.data;
  },

  // Delete customer
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`${BASE_PATH}/${id}`);
  },

  // Search customers
  search: async (query: string): Promise<PaginatedResponse<Customer>> => {
    const response = await apiClient.get<PaginatedResponse<Customer>>(BASE_PATH, {
      params: { search: query },
    });
    return response.data;
  },

  // Update customer flags
  updateFlags: async (
    id: string,
    flags: {
      is_priority?: boolean;
      is_red_flag?: boolean;
      is_slow_payer?: boolean;
    }
  ): Promise<Customer> => {
    const response = await apiClient.put<Customer>(`${BASE_PATH}/${id}`, flags);
    return response.data;
  },
};
