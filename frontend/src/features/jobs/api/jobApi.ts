import { apiClient } from '@/core/api';
import type { PaginatedResponse } from '@/core/api';
import type {
  Job,
  JobCreate,
  JobUpdate,
  JobStatusUpdate,
  JobListParams,
  JobFinancials,
} from '../types';

const BASE_PATH = '/jobs';

export const jobApi = {
  // List jobs with pagination and filters
  list: async (params?: JobListParams): Promise<PaginatedResponse<Job>> => {
    const response = await apiClient.get<PaginatedResponse<Job>>(BASE_PATH, {
      params,
    });
    return response.data;
  },

  // Get single job by ID
  get: async (id: string): Promise<Job> => {
    const response = await apiClient.get<Job>(`${BASE_PATH}/${id}`);
    return response.data;
  },

  // Create new job
  create: async (data: JobCreate): Promise<Job> => {
    const response = await apiClient.post<Job>(BASE_PATH, data);
    return response.data;
  },

  // Update existing job
  update: async (id: string, data: JobUpdate): Promise<Job> => {
    const response = await apiClient.put<Job>(`${BASE_PATH}/${id}`, data);
    return response.data;
  },

  // Update job status
  updateStatus: async (id: string, data: JobStatusUpdate): Promise<Job> => {
    const response = await apiClient.put<Job>(`${BASE_PATH}/${id}/status`, data);
    return response.data;
  },

  // Delete job
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`${BASE_PATH}/${id}`);
  },

  // Get jobs ready to schedule
  getReadyToSchedule: async (): Promise<PaginatedResponse<Job>> => {
    const response = await apiClient.get<PaginatedResponse<Job>>(BASE_PATH, {
      params: { category: 'ready_to_schedule', status: 'to_be_scheduled' },
    });
    return response.data;
  },

  // Get jobs requiring estimate
  getRequiresEstimate: async (): Promise<PaginatedResponse<Job>> => {
    const response = await apiClient.get<PaginatedResponse<Job>>(BASE_PATH, {
      params: { category: 'requires_estimate' },
    });
    return response.data;
  },

  // Get jobs by status
  getByStatus: async (
    status: string,
    params?: Omit<JobListParams, 'status'>
  ): Promise<PaginatedResponse<Job>> => {
    const response = await apiClient.get<PaginatedResponse<Job>>(BASE_PATH, {
      params: { ...params, status },
    });
    return response.data;
  },

  // Get jobs by customer
  getByCustomer: async (
    customerId: string,
    params?: Omit<JobListParams, 'customer_id'>
  ): Promise<PaginatedResponse<Job>> => {
    const response = await apiClient.get<PaginatedResponse<Job>>(BASE_PATH, {
      params: { ...params, customer_id: customerId },
    });
    return response.data;
  },

  // Search jobs
  search: async (query: string): Promise<PaginatedResponse<Job>> => {
    const response = await apiClient.get<PaginatedResponse<Job>>(BASE_PATH, {
      params: { search: query },
    });
    return response.data;
  },

  // Approve job (mark as to_be_scheduled)
  approve: async (id: string): Promise<Job> => {
    return jobApi.updateStatus(id, { status: 'to_be_scheduled' });
  },

  // Cancel job
  cancel: async (id: string, notes?: string): Promise<Job> => {
    return jobApi.updateStatus(id, { status: 'cancelled', notes });
  },

  // Complete job
  complete: async (id: string, notes?: string): Promise<Job> => {
    return jobApi.updateStatus(id, { status: 'completed', notes });
  },

  // Close job (mark as completed)
  close: async (id: string, notes?: string): Promise<Job> => {
    return jobApi.updateStatus(id, { status: 'completed', notes });
  },

  // Get per-job financials (Req 57)
  getFinancials: async (id: string): Promise<JobFinancials> => {
    const response = await apiClient.get<JobFinancials>(`${BASE_PATH}/${id}/financials`);
    return response.data;
  },
};
