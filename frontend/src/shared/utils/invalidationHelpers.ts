/**
 * Cross-feature cache invalidation helpers.
 *
 * Centralizes the invalidation matrix so every mutation refreshes all
 * affected views. Each helper encapsulates the query keys that need
 * invalidation for a given mutation category.
 *
 * Validates: april-16th-fixes-enhancements Requirement 9
 */

import type { QueryClient } from '@tanstack/react-query';
import { leadKeys } from '@/features/leads/hooks/useLeads';
import { customerKeys, customerInvoiceKeys } from '@/features/customers/hooks/useCustomers';
import { jobKeys } from '@/features/jobs/hooks/useJobs';
import { salesKeys } from '@/features/sales/hooks';
import { pipelineKeys } from '@/features/sales/hooks/useSalesPipeline';
import { appointmentKeys } from '@/features/schedule/hooks/useAppointments';
import { dashboardKeys } from '@/features/dashboard/hooks/useDashboard';

/**
 * Invalidate after routing a lead to Jobs or Sales.
 * Called from useMoveToJobs / useMoveToSales onSuccess.
 */
export function invalidateAfterLeadRouting(
  queryClient: QueryClient,
  target: 'jobs' | 'sales'
): void {
  // Always invalidate lead lists and dashboard
  queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
  queryClient.invalidateQueries({ queryKey: leadKeys.followUpQueue() });
  queryClient.invalidateQueries({ queryKey: dashboardKeys.summary() });
  queryClient.invalidateQueries({ queryKey: dashboardKeys.metrics() });

  if (target === 'jobs') {
    queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
    queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
  } else {
    queryClient.invalidateQueries({ queryKey: salesKeys.estimates() });
    queryClient.invalidateQueries({ queryKey: pipelineKeys.lists() });
  }
}

/**
 * Invalidate after any customer mutation (create, update, delete).
 */
export function invalidateAfterCustomerMutation(
  queryClient: QueryClient,
  customerId?: string
): void {
  queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
  queryClient.invalidateQueries({ queryKey: dashboardKeys.summary() });
  queryClient.invalidateQueries({ queryKey: dashboardKeys.metrics() });
  if (customerId) {
    queryClient.invalidateQueries({ queryKey: customerKeys.detail(customerId) });
  }
}

/**
 * Invalidate after marking a lead as contacted.
 */
export function invalidateAfterMarkContacted(
  queryClient: QueryClient
): void {
  queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
  queryClient.invalidateQueries({ queryKey: leadKeys.followUpQueue() });
  queryClient.invalidateQueries({ queryKey: dashboardKeys.summary() });
  queryClient.invalidateQueries({ queryKey: dashboardKeys.metrics() });
}

/**
 * Invalidate after invoice/payment mutations.
 */
export function invalidateAfterInvoicePayment(
  queryClient: QueryClient,
  customerId?: string
): void {
  queryClient.invalidateQueries({ queryKey: dashboardKeys.summary() });
  if (customerId) {
    queryClient.invalidateQueries({
      queryKey: customerInvoiceKeys.byCustomer(customerId),
    });
    queryClient.invalidateQueries({ queryKey: customerKeys.detail(customerId) });
  }
}

/**
 * Invalidate after job lifecycle mutations (status changes, completion, etc.).
 */
export function invalidateAfterJobLifecycle(
  queryClient: QueryClient,
  customerId?: string
): void {
  queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
  queryClient.invalidateQueries({ queryKey: dashboardKeys.summary() });
  if (customerId) {
    queryClient.invalidateQueries({ queryKey: customerKeys.detail(customerId) });
  }
}

/**
 * Invalidate after sales pipeline transitions (advance, convert to job, mark lost).
 */
export function invalidateAfterSalesPipelineTransition(
  queryClient: QueryClient,
  isConversion = false
): void {
  queryClient.invalidateQueries({ queryKey: pipelineKeys.lists() });
  queryClient.invalidateQueries({ queryKey: salesKeys.estimates() });
  queryClient.invalidateQueries({ queryKey: salesKeys.metrics() });
  queryClient.invalidateQueries({ queryKey: dashboardKeys.summary() });

  if (isConversion) {
    queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
    queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
  }
}


/**
 * Invalidate after saving customer internal notes from any surface.
 *
 * Covers: Customer Detail, Sales Entry Detail, Appointment Modal.
 * Uses predicate-based invalidation for sales and appointment detail keys
 * since we may not know the specific IDs that reference this customer.
 *
 * Validates: internal-notes-simplification Requirement 6
 */
export function invalidateAfterCustomerInternalNotesSave(
  queryClient: QueryClient,
  customerId: string
): void {
  // Customer queries
  queryClient.invalidateQueries({ queryKey: customerKeys.detail(customerId) });
  queryClient.invalidateQueries({ queryKey: customerKeys.lists() });

  // Sales queries — invalidate all estimate lists and use predicate for details
  // since we don't know which sales entries reference this customer
  queryClient.invalidateQueries({ queryKey: salesKeys.estimates() });
  queryClient.invalidateQueries({
    predicate: (query) => {
      const key = query.queryKey;
      // Match salesKeys.estimateDetail pattern: ['sales', 'estimates', 'detail', id]
      if (
        key[0] === 'sales' &&
        key[1] === 'estimates' &&
        key[2] === 'detail'
      ) {
        const data = query.state.data as
          | { customer?: { id?: string } }
          | undefined;
        return data?.customer?.id === customerId;
      }
      return false;
    },
  });

  // Appointment queries — invalidate lists and predicate-match details
  queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
  queryClient.invalidateQueries({
    predicate: (query) => {
      const key = query.queryKey;
      // Match appointmentKeys.detail pattern: ['appointments', 'detail', id]
      if (
        key[0] === 'appointments' &&
        key[1] === 'detail'
      ) {
        const data = query.state.data as
          | { customer?: { id?: string }; customer_id?: string }
          | undefined;
        return (
          data?.customer?.id === customerId ||
          data?.customer_id === customerId
        );
      }
      return false;
    },
  });
}
