import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { contractRenewalsApi } from '../api/contractRenewalsApi';
import type { ProposedJobModification } from '../types';

export const renewalKeys = {
  all: ['contract-renewals'] as const,
  lists: () => [...renewalKeys.all, 'list'] as const,
  list: (params?: { status?: string }) => [...renewalKeys.lists(), params] as const,
  detail: (id: string) => [...renewalKeys.all, 'detail', id] as const,
};

export function useRenewalProposals(params?: { status?: string; skip?: number; limit?: number }) {
  return useQuery({
    queryKey: renewalKeys.list(params),
    queryFn: () => contractRenewalsApi.list(params),
  });
}

export function useRenewalProposal(id: string) {
  return useQuery({
    queryKey: renewalKeys.detail(id),
    queryFn: () => contractRenewalsApi.get(id),
    enabled: !!id,
  });
}

export function useApproveAll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => contractRenewalsApi.approveAll(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: renewalKeys.all }); },
  });
}

export function useRejectAll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => contractRenewalsApi.rejectAll(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: renewalKeys.all }); },
  });
}

export function useApproveJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ proposalId, jobId, modifications }: { proposalId: string; jobId: string; modifications?: ProposedJobModification }) =>
      contractRenewalsApi.approveJob(proposalId, jobId, modifications),
    onSuccess: () => { qc.invalidateQueries({ queryKey: renewalKeys.all }); },
  });
}

export function useRejectJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ proposalId, jobId }: { proposalId: string; jobId: string }) =>
      contractRenewalsApi.rejectJob(proposalId, jobId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: renewalKeys.all }); },
  });
}

export function useModifyJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ proposalId, jobId, modifications }: { proposalId: string; jobId: string; modifications: ProposedJobModification }) =>
      contractRenewalsApi.modifyJob(proposalId, jobId, modifications),
    onSuccess: () => { qc.invalidateQueries({ queryKey: renewalKeys.all }); },
  });
}
