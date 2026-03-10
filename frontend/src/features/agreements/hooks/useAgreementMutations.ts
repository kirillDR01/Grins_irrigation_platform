import { useMutation, useQueryClient } from '@tanstack/react-query';
import { agreementsApi } from '../api/agreementsApi';
import type { AgreementStatusUpdateRequest, AgreementRenewalRejectRequest } from '../types';
import { agreementKeys } from './useAgreements';

export function useUpdateAgreementStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AgreementStatusUpdateRequest }) =>
      agreementsApi.updateStatus(id, data),
    onSuccess: (updated) => {
      qc.setQueryData(agreementKeys.detail(updated.id), updated);
      qc.invalidateQueries({ queryKey: agreementKeys.lists() });
      qc.invalidateQueries({ queryKey: agreementKeys.metrics() });
      qc.invalidateQueries({ queryKey: agreementKeys.renewalPipeline() });
      qc.invalidateQueries({ queryKey: agreementKeys.failedPayments() });
    },
  });
}

export function useApproveRenewal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => agreementsApi.approveRenewal(id),
    onSuccess: (updated) => {
      qc.setQueryData(agreementKeys.detail(updated.id), updated);
      qc.invalidateQueries({ queryKey: agreementKeys.lists() });
      qc.invalidateQueries({ queryKey: agreementKeys.renewalPipeline() });
      qc.invalidateQueries({ queryKey: agreementKeys.metrics() });
    },
  });
}

export function useRejectRenewal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data?: AgreementRenewalRejectRequest }) =>
      agreementsApi.rejectRenewal(id, data),
    onSuccess: (updated) => {
      qc.setQueryData(agreementKeys.detail(updated.id), updated);
      qc.invalidateQueries({ queryKey: agreementKeys.lists() });
      qc.invalidateQueries({ queryKey: agreementKeys.renewalPipeline() });
      qc.invalidateQueries({ queryKey: agreementKeys.metrics() });
    },
  });
}

export function useUpdateNotes() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes: string | null }) =>
      agreementsApi.updateNotes(id, notes),
    onSuccess: (updated) => {
      qc.setQueryData(agreementKeys.detail(updated.id), updated);
    },
  });
}
