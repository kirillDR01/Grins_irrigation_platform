import { apiClient } from '@/core/api';
import type { RenewalProposal, ProposedJob, ProposedJobModification } from '../types';

export const contractRenewalsApi = {
  list: async (params?: { status?: string; skip?: number; limit?: number }): Promise<RenewalProposal[]> => {
    const response = await apiClient.get<RenewalProposal[]>('/contract-renewals', { params });
    return response.data;
  },

  get: async (id: string): Promise<RenewalProposal> => {
    const response = await apiClient.get<RenewalProposal>(`/contract-renewals/${id}`);
    return response.data;
  },

  approveAll: async (id: string): Promise<RenewalProposal> => {
    const response = await apiClient.post<RenewalProposal>(`/contract-renewals/${id}/approve-all`);
    return response.data;
  },

  rejectAll: async (id: string): Promise<RenewalProposal> => {
    const response = await apiClient.post<RenewalProposal>(`/contract-renewals/${id}/reject-all`);
    return response.data;
  },

  approveJob: async (proposalId: string, jobId: string, modifications?: ProposedJobModification): Promise<ProposedJob> => {
    const response = await apiClient.post<ProposedJob>(
      `/contract-renewals/${proposalId}/jobs/${jobId}/approve`,
      modifications ?? null,
    );
    return response.data;
  },

  rejectJob: async (proposalId: string, jobId: string): Promise<ProposedJob> => {
    const response = await apiClient.post<ProposedJob>(`/contract-renewals/${proposalId}/jobs/${jobId}/reject`);
    return response.data;
  },

  modifyJob: async (proposalId: string, jobId: string, modifications: ProposedJobModification): Promise<ProposedJob> => {
    const response = await apiClient.put<ProposedJob>(
      `/contract-renewals/${proposalId}/jobs/${jobId}`,
      modifications,
    );
    return response.data;
  },
};
