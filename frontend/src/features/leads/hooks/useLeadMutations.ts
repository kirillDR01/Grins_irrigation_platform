import { useMutation, useQueryClient } from '@tanstack/react-query';
import { leadApi } from '../api/leadApi';
import type { LeadUpdate, LeadConversionRequest } from '../types';
import { leadKeys } from './useLeads';

// Update lead mutation (status, assignment, notes)
export function useUpdateLead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: LeadUpdate }) =>
      leadApi.update(id, data),
    onSuccess: (updatedLead) => {
      queryClient.setQueryData(leadKeys.detail(updatedLead.id), updatedLead);
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
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
    },
  });
}
