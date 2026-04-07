import { useMutation, useQueryClient } from '@tanstack/react-query';
import { leadApi } from '../api/leadApi';
import type { LeadUpdate, LeadConversionRequest, FromCallRequest, BulkOutreachRequest, CreateEstimateRequest, CreateContractRequest, ManualLeadCreateRequest } from '../types';
import { leadKeys } from './useLeads';

// Update lead mutation (status, assignment, notes, intake_tag)
export function useUpdateLead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: LeadUpdate }) =>
      leadApi.update(id, data),
    onSuccess: (updatedLead) => {
      queryClient.setQueryData(leadKeys.detail(updatedLead.id), updatedLead);
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      queryClient.invalidateQueries({ queryKey: leadKeys.followUpQueue() });
    },
  });
}

// Convert lead to customer mutation
export function useConvertLead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: LeadConversionRequest }) =>
      leadApi.convert(id, data),
    onSuccess: (_result, variables) => {
      queryClient.invalidateQueries({ queryKey: leadKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      queryClient.invalidateQueries({ queryKey: leadKeys.followUpQueue() });
    },
  });
}

// Delete lead mutation
export function useDeleteLead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => leadApi.delete(id),
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: leadKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      queryClient.invalidateQueries({ queryKey: leadKeys.followUpQueue() });
    },
  });
}

// Create lead from phone call (admin-only)
export function useCreateFromCall() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: FromCallRequest) => leadApi.createFromCall(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      queryClient.invalidateQueries({ queryKey: leadKeys.followUpQueue() });
    },
  });
}

// Create lead manually (admin-only)
export function useCreateManualLead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ManualLeadCreateRequest) => leadApi.createManual(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      queryClient.invalidateQueries({ queryKey: leadKeys.followUpQueue() });
    },
  });
}

// Bulk outreach mutation (Req 14)
export function useBulkOutreach() {
  return useMutation({
    mutationFn: (data: BulkOutreachRequest) => leadApi.bulkOutreach(data),
  });
}

// Upload attachment mutation (Req 15)
export function useUploadAttachment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ leadId, file, attachmentType }: { leadId: string; file: File; attachmentType: string }) =>
      leadApi.uploadAttachment(leadId, file, attachmentType),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: leadKeys.attachments(variables.leadId) });
    },
  });
}

// Delete attachment mutation (Req 15)
export function useDeleteAttachment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ leadId, attachmentId }: { leadId: string; attachmentId: string }) =>
      leadApi.deleteAttachment(leadId, attachmentId),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: leadKeys.attachments(variables.leadId) });
    },
  });
}

// Create estimate mutation (Req 17)
export function useCreateEstimate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateEstimateRequest) => leadApi.createEstimate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
    },
  });
}

// Create contract mutation (Req 17)
export function useCreateContract() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateContractRequest) => leadApi.createContract(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
    },
  });
}
