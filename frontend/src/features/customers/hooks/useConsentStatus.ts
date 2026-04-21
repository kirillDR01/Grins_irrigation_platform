/**
 * TanStack Query hook for the derived consent-status snapshot (Gap 06).
 *
 * Drives the shared `OptOutBadge` and disables outbound SMS buttons
 * when the customer has opted out or has a pending informal-opt-out
 * alert. Cached for 30 seconds per the gap-06 spec — short enough that
 * an admin action (confirm / dismiss) reflects within the same session,
 * long enough to avoid per-render thrash on queues with many rows.
 */
import { useQuery } from '@tanstack/react-query';

import { customerApi } from '../api/customerApi';

export const consentStatusKeys = {
  all: ['consent-status'] as const,
  byCustomer: (id: string) => [...consentStatusKeys.all, id] as const,
};

export function useCustomerConsentStatus(customerId: string | null | undefined) {
  return useQuery({
    queryKey: customerId ? consentStatusKeys.byCustomer(customerId) : consentStatusKeys.all,
    queryFn: () => customerApi.getConsentStatus(customerId as string),
    enabled: Boolean(customerId),
    staleTime: 30_000,
  });
}
