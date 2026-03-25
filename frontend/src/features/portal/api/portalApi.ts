import { apiClient } from '@/core/api';
import type {
  PortalEstimate,
  PortalContract,
  PortalInvoice,
  PortalApproveRequest,
  PortalRejectRequest,
  PortalSignRequest,
} from '../types';

export const portalApi = {
  // Estimate portal (public, no auth)
  getEstimate: async (token: string): Promise<PortalEstimate> => {
    const response = await apiClient.get<PortalEstimate>(`/portal/estimates/${token}`);
    return response.data;
  },

  approveEstimate: async (token: string, data?: PortalApproveRequest): Promise<void> => {
    await apiClient.post(`/portal/estimates/${token}/approve`, data ?? {});
  },

  rejectEstimate: async (token: string, data?: PortalRejectRequest): Promise<void> => {
    await apiClient.post(`/portal/estimates/${token}/reject`, data ?? {});
  },

  // Contract portal (public, no auth)
  getContract: async (token: string): Promise<PortalContract> => {
    const response = await apiClient.get<PortalContract>(`/portal/contracts/${token}`);
    return response.data;
  },

  signContract: async (token: string, data: PortalSignRequest): Promise<void> => {
    await apiClient.post(`/portal/contracts/${token}/sign`, data);
  },

  // Invoice portal (public, no auth)
  getInvoice: async (token: string): Promise<PortalInvoice> => {
    const response = await apiClient.get<PortalInvoice>(`/portal/invoices/${token}`);
    return response.data;
  },
};
