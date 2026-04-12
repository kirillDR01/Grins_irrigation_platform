import { apiClient } from '@/core/api';
import type { PaginatedResponse } from '@/core/api';
import type {
  Job,
  JobCompleteResponse,
  JobCreate,
  JobUpdate,
  JobStatusUpdate,
  JobListParams,
  JobFinancials,
  JobNoteCreate,
  JobNoteResponse,
  JobReviewPushResponse,
  JobPhoto,
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

  // Complete job via dedicated endpoint (Req 21.2, 27.3-27.5)
  completeJob: async (id: string, force = false): Promise<JobCompleteResponse> => {
    const response = await apiClient.post<JobCompleteResponse>(
      `${BASE_PATH}/${id}/complete`,
      { force },
    );
    return response.data;
  },

  // Create invoice from job via dedicated endpoint (Req 21.1)
  createInvoice: async (id: string): Promise<Record<string, unknown>> => {
    const response = await apiClient.post<Record<string, unknown>>(`${BASE_PATH}/${id}/invoice`);
    return response.data;
  },

  // On My Way — send SMS and log timestamp (Req 27.1)
  onMyWay: async (id: string): Promise<Job> => {
    const response = await apiClient.post<Job>(`${BASE_PATH}/${id}/on-my-way`);
    return response.data;
  },

  // Job Started — log timestamp (Req 27.2)
  jobStarted: async (id: string): Promise<Job> => {
    const response = await apiClient.post<Job>(`${BASE_PATH}/${id}/started`);
    return response.data;
  },

  // Add note to job (Req 26.3)
  addNote: async (id: string, data: JobNoteCreate): Promise<JobNoteResponse> => {
    const response = await apiClient.post<JobNoteResponse>(`${BASE_PATH}/${id}/notes`, data);
    return response.data;
  },

  // Upload photo linked to job (Req 26.3)
  uploadPhoto: async (id: string, file: File, caption?: string): Promise<JobPhoto> => {
    const formData = new FormData();
    formData.append('file', file);
    const params = caption ? { caption } : undefined;
    const response = await apiClient.post<JobPhoto>(`${BASE_PATH}/${id}/photos`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params,
    });
    return response.data;
  },

  // Send Google review push SMS (Req 26.4)
  reviewPush: async (id: string): Promise<JobReviewPushResponse> => {
    const response = await apiClient.post<JobReviewPushResponse>(`${BASE_PATH}/${id}/review-push`);
    return response.data;
  },
};
