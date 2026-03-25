import { useQuery } from '@tanstack/react-query';
import { agreementsApi } from '../api/agreementsApi';
import type { AgreementListParams } from '../types';

// Query key factories
export const agreementKeys = {
  all: ['agreements'] as const,
  lists: () => [...agreementKeys.all, 'list'] as const,
  list: (params?: AgreementListParams) => [...agreementKeys.lists(), params] as const,
  details: () => [...agreementKeys.all, 'detail'] as const,
  detail: (id: string) => [...agreementKeys.details(), id] as const,
  metrics: () => [...agreementKeys.all, 'metrics'] as const,
  mrrHistory: () => [...agreementKeys.all, 'mrr-history'] as const,
  tierDistribution: () => [...agreementKeys.all, 'tier-distribution'] as const,
  renewalPipeline: () => [...agreementKeys.all, 'renewal-pipeline'] as const,
  failedPayments: () => [...agreementKeys.all, 'failed-payments'] as const,
  annualNoticeDue: () => [...agreementKeys.all, 'annual-notice-due'] as const,
  compliance: (id: string) => [...agreementKeys.all, 'compliance', id] as const,
  customerCompliance: (customerId: string) => [...agreementKeys.all, 'customer-compliance', customerId] as const,
};

export const tierKeys = {
  all: ['agreement-tiers'] as const,
  lists: () => [...tierKeys.all, 'list'] as const,
  details: () => [...tierKeys.all, 'detail'] as const,
  detail: (id: string) => [...tierKeys.details(), id] as const,
};

// List agreements with pagination and filters
export function useAgreements(params?: AgreementListParams) {
  return useQuery({
    queryKey: agreementKeys.list(params),
    queryFn: () => agreementsApi.list(params),
  });
}

// Get single agreement by ID
export function useAgreement(id: string) {
  return useQuery({
    queryKey: agreementKeys.detail(id),
    queryFn: () => agreementsApi.get(id),
    enabled: !!id,
  });
}

// Get agreement metrics
export function useAgreementMetrics() {
  return useQuery({
    queryKey: agreementKeys.metrics(),
    queryFn: () => agreementsApi.getMetrics(),
  });
}

// Get renewal pipeline
export function useRenewalPipeline() {
  return useQuery({
    queryKey: agreementKeys.renewalPipeline(),
    queryFn: () => agreementsApi.getRenewalPipeline(),
  });
}

// Get failed payments
export function useFailedPayments() {
  return useQuery({
    queryKey: agreementKeys.failedPayments(),
    queryFn: () => agreementsApi.getFailedPayments(),
  });
}

// Get MRR history (trailing 12 months)
export function useMrrHistory() {
  return useQuery({
    queryKey: agreementKeys.mrrHistory(),
    queryFn: () => agreementsApi.getMrrHistory(),
  });
}

// Get tier distribution
export function useTierDistribution() {
  return useQuery({
    queryKey: agreementKeys.tierDistribution(),
    queryFn: () => agreementsApi.getTierDistribution(),
  });
}

// Get annual notice due
export function useAnnualNoticeDue() {
  return useQuery({
    queryKey: agreementKeys.annualNoticeDue(),
    queryFn: () => agreementsApi.getAnnualNoticeDue(),
  });
}

// Get onboarding incomplete (pending agreements with no property)
export function useOnboardingIncomplete() {
  return useQuery({
    queryKey: agreementKeys.list({ status: 'pending' as const, page: 1, page_size: 100 }),
    queryFn: () => agreementsApi.list({ status: 'pending', page: 1, page_size: 100 }),
    select: (data) => data?.items?.filter((a) => !a.property_id) ?? [],
  });
}

// Get compliance records for an agreement
export function useAgreementCompliance(agreementId: string) {
  return useQuery({
    queryKey: agreementKeys.compliance(agreementId),
    queryFn: () => agreementsApi.getCompliance(agreementId),
    enabled: !!agreementId,
  });
}
