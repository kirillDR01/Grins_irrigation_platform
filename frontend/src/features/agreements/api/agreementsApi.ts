import { apiClient } from '@/core/api';
import type { PaginatedResponse } from '@/core/api';
import type {
  Agreement,
  AgreementDetail,
  AgreementListParams,
  AgreementMetrics,
  AgreementStatusUpdateRequest,
  AgreementRenewalRejectRequest,
  AgreementTier,
  DisclosureRecord,
  MrrHistory,
  TierDistribution,
} from '../types';

const BASE_PATH = '/agreements';
const TIER_PATH = '/agreement-tiers';

export const agreementsApi = {
  list: async (params?: AgreementListParams): Promise<PaginatedResponse<Agreement>> => {
    const response = await apiClient.get<PaginatedResponse<Agreement>>(BASE_PATH, { params });
    return response.data;
  },

  get: async (id: string): Promise<AgreementDetail> => {
    const response = await apiClient.get<AgreementDetail>(`${BASE_PATH}/${id}`);
    return response.data;
  },

  updateStatus: async (id: string, data: AgreementStatusUpdateRequest): Promise<AgreementDetail> => {
    const response = await apiClient.patch<AgreementDetail>(`${BASE_PATH}/${id}/status`, data);
    return response.data;
  },

  updateNotes: async (id: string, notes: string | null): Promise<AgreementDetail> => {
    const response = await apiClient.patch<AgreementDetail>(`${BASE_PATH}/${id}/notes`, { notes });
    return response.data;
  },

  approveRenewal: async (id: string): Promise<AgreementDetail> => {
    const response = await apiClient.post<AgreementDetail>(`${BASE_PATH}/${id}/approve-renewal`);
    return response.data;
  },

  rejectRenewal: async (id: string, data?: AgreementRenewalRejectRequest): Promise<AgreementDetail> => {
    const response = await apiClient.post<AgreementDetail>(`${BASE_PATH}/${id}/reject-renewal`, data);
    return response.data;
  },

  getMetrics: async (): Promise<AgreementMetrics> => {
    const response = await apiClient.get<AgreementMetrics>(`${BASE_PATH}/metrics/summary`);
    return response.data;
  },

  getMrrHistory: async (): Promise<MrrHistory> => {
    const response = await apiClient.get<MrrHistory>(`${BASE_PATH}/metrics/mrr-history`);
    return response.data;
  },

  getTierDistribution: async (): Promise<TierDistribution> => {
    const response = await apiClient.get<TierDistribution>(`${BASE_PATH}/metrics/tier-distribution`);
    return response.data;
  },

  getRenewalPipeline: async (): Promise<Agreement[]> => {
    const response = await apiClient.get<Agreement[]>(`${BASE_PATH}/queues/renewal-pipeline`);
    return response.data;
  },

  getFailedPayments: async (): Promise<Agreement[]> => {
    const response = await apiClient.get<Agreement[]>(`${BASE_PATH}/queues/failed-payments`);
    return response.data;
  },

  getCompliance: async (agreementId: string): Promise<DisclosureRecord[]> => {
    const response = await apiClient.get<DisclosureRecord[]>(`${BASE_PATH}/${agreementId}/compliance`);
    return response.data;
  },

  getCustomerCompliance: async (customerId: string): Promise<DisclosureRecord[]> => {
    const response = await apiClient.get<DisclosureRecord[]>(`/compliance/customer/${customerId}`);
    return response.data;
  },

  getAnnualNoticeDue: async (): Promise<Agreement[]> => {
    const response = await apiClient.get<Agreement[]>(`${BASE_PATH}/queues/annual-notice-due`);
    return response.data;
  },

  // Tier endpoints
  listTiers: async (): Promise<AgreementTier[]> => {
    const response = await apiClient.get<AgreementTier[]>(TIER_PATH);
    return response.data;
  },

  getTier: async (id: string): Promise<AgreementTier> => {
    const response = await apiClient.get<AgreementTier>(`${TIER_PATH}/${id}`);
    return response.data;
  },
};
