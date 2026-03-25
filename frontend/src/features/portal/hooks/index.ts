import { useQuery, useMutation } from '@tanstack/react-query';
import { portalApi } from '../api/portalApi';
import type { PortalApproveRequest, PortalRejectRequest, PortalSignRequest } from '../types';

// Query key factory
export const portalKeys = {
  all: ['portal'] as const,
  estimate: (token: string) => [...portalKeys.all, 'estimate', token] as const,
  contract: (token: string) => [...portalKeys.all, 'contract', token] as const,
  invoice: (token: string) => [...portalKeys.all, 'invoice', token] as const,
};

// Estimate hooks
export function usePortalEstimate(token: string) {
  return useQuery({
    queryKey: portalKeys.estimate(token),
    queryFn: () => portalApi.getEstimate(token),
    enabled: !!token,
    retry: false,
  });
}

export function useApproveEstimate(token: string) {
  return useMutation({
    mutationFn: (data?: PortalApproveRequest) => portalApi.approveEstimate(token, data),
  });
}

export function useRejectEstimate(token: string) {
  return useMutation({
    mutationFn: (data?: PortalRejectRequest) => portalApi.rejectEstimate(token, data),
  });
}

// Contract hooks
export function usePortalContract(token: string) {
  return useQuery({
    queryKey: portalKeys.contract(token),
    queryFn: () => portalApi.getContract(token),
    enabled: !!token,
    retry: false,
  });
}

export function useSignContract(token: string) {
  return useMutation({
    mutationFn: (data: PortalSignRequest) => portalApi.signContract(token, data),
  });
}

// Invoice hooks
export function usePortalInvoice(token: string) {
  return useQuery({
    queryKey: portalKeys.invoice(token),
    queryFn: () => portalApi.getInvoice(token),
    enabled: !!token,
    retry: false,
  });
}
