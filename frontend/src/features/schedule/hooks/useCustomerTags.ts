/**
 * Hooks for customer tag queries and mutations.
 * Requirements: 12.4, 12.5, 13.9, 13.10
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { customerApi } from '@/features/customers/api/customerApi';
import { customerKeys } from '@/features/customers/hooks/useCustomers';
import { jobKeys } from '@/features/jobs/hooks/useJobs';
import { appointmentKeys } from '@/features/schedule/hooks/useAppointments';
import { pipelineKeys } from '@/features/sales/hooks/useSalesPipeline';
import type { CustomerTag, TagSaveRequest } from '../types';

export const customerTagKeys = {
  all: ['customer-tags'] as const,
  byCustomer: (customerId: string) =>
    [...customerTagKeys.all, customerId] as const,
};

/**
 * Query hook: fetch tags for a customer.
 */
export function useCustomerTags(customerId: string | undefined) {
  return useQuery({
    queryKey: customerTagKeys.byCustomer(customerId ?? ''),
    queryFn: () => customerApi.getTags(customerId!),
    enabled: !!customerId,
  });
}

/**
 * Mutation hook: save (PUT) tags for a customer with optimistic update.
 */
export function useSaveCustomerTags() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      customerId,
      data,
    }: {
      customerId: string;
      data: TagSaveRequest;
    }) => customerApi.saveTags(customerId, data),

    onMutate: async ({ customerId, data }) => {
      const queryKey = customerTagKeys.byCustomer(customerId);
      await queryClient.cancelQueries({ queryKey });

      const previous = queryClient.getQueryData<CustomerTag[]>(queryKey);

      // Optimistic update: replace manual tags with incoming, keep system tags
      const systemTags =
        previous?.filter((t) => t.source === 'system') ?? [];
      const optimistic: CustomerTag[] = [
        ...systemTags,
        ...data.tags.map((t, i) => ({
          id: `optimistic-${i}`,
          customer_id: customerId,
          label: t.label,
          tone: t.tone,
          source: 'manual' as const,
          created_at: new Date().toISOString(),
        })),
      ];
      queryClient.setQueryData(queryKey, optimistic);

      return { previous, queryKey };
    },

    onError: (_err, _vars, context) => {
      if (context) {
        queryClient.setQueryData(context.queryKey, context.previous);
      }
    },

    onSettled: (_data, _err, { customerId }) => {
      // Cluster A: Job/Appointment/Sales responses denormalize customer_tags.
      // Invalidate every list so the freshly saved tag-set surfaces without
      // a manual refresh.
      queryClient.invalidateQueries({
        queryKey: customerTagKeys.byCustomer(customerId),
      });
      queryClient.invalidateQueries({ queryKey: customerKeys.detail(customerId) });
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}
