import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { marketingApi } from '../api/marketingApi';
import type {
  DateRangeFilter,
  CampaignCreateRequest,
  CampaignListParams,
  MarketingBudgetCreateRequest,
  BudgetListParams,
  QRCodeRequest,
} from '../types';

// Query key factory
export const marketingKeys = {
  all: ['marketing'] as const,
  leadAnalytics: (dateRange?: DateRangeFilter) =>
    [...marketingKeys.all, 'lead-analytics', dateRange] as const,
  cac: (params?: { start_date?: string; end_date?: string }) =>
    [...marketingKeys.all, 'cac', params] as const,
  campaigns: () => [...marketingKeys.all, 'campaigns'] as const,
  campaignList: (params?: CampaignListParams) => [...marketingKeys.campaigns(), params] as const,
  campaignStats: (id: string) => [...marketingKeys.all, 'campaign-stats', id] as const,
  budgets: () => [...marketingKeys.all, 'budgets'] as const,
  budgetList: (params?: BudgetListParams) => [...marketingKeys.budgets(), params] as const,
};

// Lead analytics
export function useLeadAnalytics(dateRange?: DateRangeFilter) {
  return useQuery({
    queryKey: marketingKeys.leadAnalytics(dateRange),
    queryFn: () => marketingApi.getLeadAnalytics(dateRange),
  });
}

// Customer acquisition cost
export function useCAC(params?: { start_date?: string; end_date?: string }) {
  return useQuery({
    queryKey: marketingKeys.cac(params),
    queryFn: () => marketingApi.getCAC(params),
  });
}

// Campaigns
export function useCampaigns(params?: CampaignListParams) {
  return useQuery({
    queryKey: marketingKeys.campaignList(params),
    queryFn: () => marketingApi.getCampaigns(params),
  });
}

export function useCampaignStats(id: string) {
  return useQuery({
    queryKey: marketingKeys.campaignStats(id),
    queryFn: () => marketingApi.getCampaignStats(id),
    enabled: !!id,
  });
}

export function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CampaignCreateRequest) => marketingApi.createCampaign(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: marketingKeys.campaigns() });
    },
  });
}

export function useUpdateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CampaignCreateRequest> }) =>
      marketingApi.updateCampaign(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: marketingKeys.campaigns() });
    },
  });
}

export function useDeleteCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => marketingApi.deleteCampaign(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: marketingKeys.campaigns() });
    },
  });
}

export function useSendCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => marketingApi.sendCampaign(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: marketingKeys.campaigns() });
      qc.invalidateQueries({ queryKey: marketingKeys.campaignStats(id) });
    },
  });
}

// Budgets
export function useBudgets(params?: BudgetListParams) {
  return useQuery({
    queryKey: marketingKeys.budgetList(params),
    queryFn: () => marketingApi.getBudgets(params),
  });
}

export function useCreateBudget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MarketingBudgetCreateRequest) => marketingApi.createBudget(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: marketingKeys.budgets() });
    },
  });
}

export function useUpdateBudget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<MarketingBudgetCreateRequest> }) =>
      marketingApi.updateBudget(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: marketingKeys.budgets() });
    },
  });
}

export function useDeleteBudget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => marketingApi.deleteBudget(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: marketingKeys.budgets() });
    },
  });
}

// QR Code generation
export function useGenerateQRCode() {
  return useMutation({
    mutationFn: (data: QRCodeRequest) => marketingApi.generateQRCode(data),
  });
}
