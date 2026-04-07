import { apiClient } from '@/core/api';
import type {
  Lead,
  LeadListParams,
  LeadUpdate,
  LeadConversionRequest,
  LeadConversionResponse,
  PaginatedLeadResponse,
  PaginatedFollowUpResponse,
  FromCallRequest,
  LeadMetricsBySourceResponse,
  LeadMetricsBySourceParams,
  LeadAttachment,
  BulkOutreachRequest,
  BulkOutreachResponse,
  EstimateTemplate,
  ContractTemplate,
  CreateEstimateRequest,
  CreateContractRequest,
  ManualLeadCreateRequest,
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

  // Update lead (status, assignment, notes, intake_tag)
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

  // Follow-up queue
  followUpQueue: async (): Promise<PaginatedFollowUpResponse> => {
    const response = await apiClient.get<PaginatedFollowUpResponse>(
      `${BASE_PATH}/follow-up-queue`
    );
    return response.data;
  },

  // Create lead from phone call (admin-only)
  createFromCall: async (data: FromCallRequest): Promise<Lead> => {
    const response = await apiClient.post<Lead>(`${BASE_PATH}/from-call`, data);
    return response.data;
  },

  // Create lead manually (admin-only)
  createManual: async (data: ManualLeadCreateRequest): Promise<Lead> => {
    const response = await apiClient.post<Lead>(`${BASE_PATH}/manual`, data);
    return response.data;
  },

  // Get lead metrics grouped by source
  metricsBySource: async (params?: LeadMetricsBySourceParams): Promise<LeadMetricsBySourceResponse> => {
    const response = await apiClient.get<LeadMetricsBySourceResponse>(
      `${BASE_PATH}/metrics/by-source`,
      { params }
    );
    return response.data;
  },

  // Bulk outreach (Req 14)
  bulkOutreach: async (data: BulkOutreachRequest): Promise<BulkOutreachResponse> => {
    const response = await apiClient.post<BulkOutreachResponse>(
      `${BASE_PATH}/bulk-outreach`,
      data
    );
    return response.data;
  },

  // Attachments (Req 15)
  listAttachments: async (leadId: string): Promise<LeadAttachment[]> => {
    const response = await apiClient.get<LeadAttachment[]>(
      `${BASE_PATH}/${leadId}/attachments`
    );
    return response.data;
  },

  uploadAttachment: async (leadId: string, file: File, attachmentType: string): Promise<LeadAttachment> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('attachment_type', attachmentType);
    const response = await apiClient.post<LeadAttachment>(
      `${BASE_PATH}/${leadId}/attachments`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  },

  deleteAttachment: async (leadId: string, attachmentId: string): Promise<void> => {
    await apiClient.delete(`${BASE_PATH}/${leadId}/attachments/${attachmentId}`);
  },

  // Estimate templates (Req 17)
  listEstimateTemplates: async (): Promise<EstimateTemplate[]> => {
    const response = await apiClient.get<EstimateTemplate[]>('/templates/estimates');
    return response.data;
  },

  // Contract templates (Req 17)
  listContractTemplates: async (): Promise<ContractTemplate[]> => {
    const response = await apiClient.get<ContractTemplate[]>('/templates/contracts');
    return response.data;
  },

  // Create estimate for lead (Req 17)
  createEstimate: async (data: CreateEstimateRequest): Promise<unknown> => {
    const response = await apiClient.post('/estimates', data);
    return response.data;
  },

  // Create contract for lead (Req 17)
  createContract: async (data: CreateContractRequest): Promise<unknown> => {
    const response = await apiClient.post('/contracts', data);
    return response.data;
  },
};
