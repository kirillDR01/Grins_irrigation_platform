import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { serviceApi } from '../api/serviceApi';
import type {
  ServiceOfferingCreate,
  ServiceOfferingListParams,
  ServiceOfferingUpdate,
} from '../types';

// Query-key factory mirrors the invoiceKeys pattern.
export const serviceKeys = {
  all: ['service-offerings'] as const,
  lists: () => [...serviceKeys.all, 'list'] as const,
  list: (params?: ServiceOfferingListParams) =>
    [...serviceKeys.lists(), params] as const,
  details: () => [...serviceKeys.all, 'detail'] as const,
  detail: (id: string) => [...serviceKeys.details(), id] as const,
  history: (id: string) => [...serviceKeys.all, 'history', id] as const,
  export: () => [...serviceKeys.all, 'export'] as const,
};

export function useServiceOfferings(params?: ServiceOfferingListParams) {
  return useQuery({
    queryKey: serviceKeys.list(params),
    queryFn: () => serviceApi.list(params),
  });
}

export function useServiceOffering(id: string) {
  return useQuery({
    queryKey: serviceKeys.detail(id),
    queryFn: () => serviceApi.get(id),
    enabled: !!id,
  });
}

export function useServiceOfferingHistory(id: string) {
  return useQuery({
    queryKey: serviceKeys.history(id),
    queryFn: () => serviceApi.history(id),
    enabled: !!id,
  });
}

export function useCreateServiceOffering() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ServiceOfferingCreate) => serviceApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: serviceKeys.all });
    },
  });
}

export function useUpdateServiceOffering() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ServiceOfferingUpdate }) =>
      serviceApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: serviceKeys.lists() });
      queryClient.invalidateQueries({ queryKey: serviceKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: serviceKeys.history(id) });
      queryClient.invalidateQueries({ queryKey: serviceKeys.export() });
    },
  });
}

export function useDeactivateServiceOffering() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => serviceApi.deactivate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: serviceKeys.all });
    },
  });
}
