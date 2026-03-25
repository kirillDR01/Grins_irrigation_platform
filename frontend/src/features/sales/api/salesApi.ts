import { apiClient } from '@/core/api';
import type { PaginatedResponse } from '@/core/api';
import type {
  SalesMetrics,
  EstimateListItem,
  EstimateCreateRequest,
  MediaItem,
  MediaListParams,
  FollowUpItem,
  EstimateTemplate,
  EstimateDetail,
} from '../types';

export const salesApi = {
  // Sales pipeline metrics
  getMetrics: async (): Promise<SalesMetrics> => {
    const response = await apiClient.get<SalesMetrics>('/sales/metrics');
    return response.data;
  },

  // Estimate list with optional filters
  getEstimates: async (params?: Record<string, string>): Promise<PaginatedResponse<EstimateListItem>> => {
    const response = await apiClient.get<PaginatedResponse<EstimateListItem>>('/estimates', { params });
    return response.data;
  },

  // Create a new estimate
  createEstimate: async (data: EstimateCreateRequest): Promise<EstimateListItem> => {
    const response = await apiClient.post<EstimateListItem>('/estimates', data);
    return response.data;
  },

  // Send estimate to customer
  sendEstimate: async (id: string): Promise<void> => {
    await apiClient.post(`/estimates/${id}/send`);
  },

  // Estimate templates
  getTemplates: async (): Promise<EstimateTemplate[]> => {
    const response = await apiClient.get<EstimateTemplate[]>('/templates/estimates');
    return response.data;
  },

  // Media library
  getMedia: async (params?: MediaListParams): Promise<PaginatedResponse<MediaItem>> => {
    const response = await apiClient.get<PaginatedResponse<MediaItem>>('/media', { params });
    return response.data;
  },

  // Upload media file
  uploadMedia: async (file: File, metadata: { category: string; media_type: string; caption?: string }): Promise<MediaItem> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', metadata.category);
    formData.append('media_type', metadata.media_type);
    if (metadata.caption) formData.append('caption', metadata.caption);
    const response = await apiClient.post<MediaItem>('/media', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  // Follow-up queue
  getFollowUps: async (): Promise<PaginatedResponse<FollowUpItem>> => {
    const response = await apiClient.get<PaginatedResponse<FollowUpItem>>('/estimates', {
      params: { needs_followup: 'true' },
    });
    return response.data;
  },

  // Estimate detail (Req 83)
  getEstimateDetail: async (id: string): Promise<EstimateDetail> => {
    const response = await apiClient.get<EstimateDetail>(`/estimates/${id}`);
    return response.data;
  },

  // Cancel estimate
  cancelEstimate: async (id: string): Promise<void> => {
    await apiClient.post(`/estimates/${id}/cancel`);
  },

  // Create job from approved estimate
  createJobFromEstimate: async (id: string): Promise<{ job_id: string }> => {
    const response = await apiClient.post<{ job_id: string }>(`/estimates/${id}/create-job`);
    return response.data;
  },
};
