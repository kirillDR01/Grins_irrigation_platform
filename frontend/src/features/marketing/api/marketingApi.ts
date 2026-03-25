import { apiClient } from '@/core/api';
import type { PaginatedResponse } from '@/core/api';
import type {
  LeadAnalytics,
  CACBySource,
  Campaign,
  CampaignCreateRequest,
  CampaignStats,
  CampaignListParams,
  MarketingBudget,
  MarketingBudgetCreateRequest,
  BudgetListParams,
  QRCodeRequest,
  QRCodeResponse,
  DateRangeFilter,
} from '../types';

export const marketingApi = {
  // Lead source analytics
  getLeadAnalytics: async (params?: DateRangeFilter): Promise<LeadAnalytics> => {
    const response = await apiClient.get<LeadAnalytics>('/marketing/lead-analytics', {
      params,
    });
    return response.data;
  },

  // Customer acquisition cost
  getCAC: async (params?: { start_date?: string; end_date?: string }): Promise<CACBySource[]> => {
    const response = await apiClient.get<CACBySource[]>('/marketing/cac', { params });
    return response.data;
  },

  // Campaign CRUD
  getCampaigns: async (params?: CampaignListParams): Promise<PaginatedResponse<Campaign>> => {
    const response = await apiClient.get<PaginatedResponse<Campaign>>('/campaigns', { params });
    return response.data;
  },

  createCampaign: async (data: CampaignCreateRequest): Promise<Campaign> => {
    const response = await apiClient.post<Campaign>('/campaigns', data);
    return response.data;
  },

  updateCampaign: async (id: string, data: Partial<CampaignCreateRequest>): Promise<Campaign> => {
    const response = await apiClient.patch<Campaign>(`/campaigns/${id}`, data);
    return response.data;
  },

  deleteCampaign: async (id: string): Promise<void> => {
    await apiClient.delete(`/campaigns/${id}`);
  },

  sendCampaign: async (id: string): Promise<void> => {
    await apiClient.post(`/campaigns/${id}/send`);
  },

  getCampaignStats: async (id: string): Promise<CampaignStats> => {
    const response = await apiClient.get<CampaignStats>(`/campaigns/${id}/stats`);
    return response.data;
  },

  // Marketing budget CRUD
  getBudgets: async (params?: BudgetListParams): Promise<PaginatedResponse<MarketingBudget>> => {
    const response = await apiClient.get<PaginatedResponse<MarketingBudget>>('/marketing/budgets', {
      params,
    });
    return response.data;
  },

  createBudget: async (data: MarketingBudgetCreateRequest): Promise<MarketingBudget> => {
    const response = await apiClient.post<MarketingBudget>('/marketing/budgets', data);
    return response.data;
  },

  updateBudget: async (
    id: string,
    data: Partial<MarketingBudgetCreateRequest>,
  ): Promise<MarketingBudget> => {
    const response = await apiClient.patch<MarketingBudget>(`/marketing/budgets/${id}`, data);
    return response.data;
  },

  deleteBudget: async (id: string): Promise<void> => {
    await apiClient.delete(`/marketing/budgets/${id}`);
  },

  // QR Code generation
  generateQRCode: async (data: QRCodeRequest): Promise<QRCodeResponse> => {
    const response = await apiClient.post<QRCodeResponse>('/marketing/qr-codes', data);
    return response.data;
  },
};
