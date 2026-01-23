import { useMutation, useQueryClient } from '@tanstack/react-query';
import { customerApi } from '../api/customerApi';
import type { CustomerCreate, CustomerUpdate } from '../types';
import { customerKeys } from './useCustomers';

// Create customer mutation
export function useCreateCustomer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CustomerCreate) => customerApi.create(data),
    onSuccess: () => {
      // Invalidate customer lists to refetch
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
    },
  });
}

// Update customer mutation
export function useUpdateCustomer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CustomerUpdate }) =>
      customerApi.update(id, data),
    onSuccess: (updatedCustomer) => {
      // Update the specific customer in cache
      queryClient.setQueryData(customerKeys.detail(updatedCustomer.id), updatedCustomer);
      // Invalidate lists to refetch
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
    },
  });
}

// Delete customer mutation
export function useDeleteCustomer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => customerApi.delete(id),
    onSuccess: (_data, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: customerKeys.detail(id) });
      // Invalidate lists to refetch
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
    },
  });
}

// Update customer flags mutation
export function useUpdateCustomerFlags() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      flags,
    }: {
      id: string;
      flags: {
        is_priority?: boolean;
        is_red_flag?: boolean;
        is_slow_payer?: boolean;
      };
    }) => customerApi.updateFlags(id, flags),
    onSuccess: (updatedCustomer) => {
      // Update the specific customer in cache
      queryClient.setQueryData(customerKeys.detail(updatedCustomer.id), updatedCustomer);
      // Invalidate lists to refetch
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
    },
  });
}
