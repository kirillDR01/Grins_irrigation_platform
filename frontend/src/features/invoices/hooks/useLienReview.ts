import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { invoiceApi } from '../api/invoiceApi';
import { invoiceKeys } from './useInvoices';
import type { LienCandidatesParams } from '../types';

/**
 * CR-5: list lien-eligible customers for the admin Review Queue.
 */
export function useLienCandidates(params?: LienCandidatesParams) {
  return useQuery({
    queryKey: invoiceKeys.lienCandidates(params),
    queryFn: () => invoiceApi.lienCandidates(params),
  });
}

/**
 * CR-5: admin-approved per-customer lien notice dispatch.
 *
 * On success, invalidates the lien candidates, overdue, and invoice list
 * caches so the row disappears from the queue and the reminder_count +
 * last_reminder_sent fields surface on the customer's invoices.
 */
export function useSendLienNotice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (customerId: string) => invoiceApi.sendLienNotice(customerId),
    onSuccess: (data) => {
      if (data.success) {
        toast.success('Lien notice sent');
      } else {
        // Service returned success=false (e.g. opted_out, no_phone)
        toast.error(`Lien notice not sent: ${data.message}`);
      }
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lienCandidates() });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.overdue() });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
    },
  });
}
