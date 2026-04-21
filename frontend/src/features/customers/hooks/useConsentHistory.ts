/**
 * TanStack Query hook for SmsConsentRecord history (Gap 06).
 *
 * Powers the ConsentHistoryPanel on CustomerDetail.
 */
import { useQuery } from '@tanstack/react-query';

import { customerApi } from '../api/customerApi';

export const consentHistoryKeys = {
  all: ['consent-history'] as const,
  byCustomer: (id: string, limit: number) =>
    [...consentHistoryKeys.all, id, limit] as const,
};

export function useCustomerConsentHistory(
  customerId: string | null | undefined,
  limit: number = 50,
) {
  return useQuery({
    queryKey: customerId
      ? consentHistoryKeys.byCustomer(customerId, limit)
      : consentHistoryKeys.all,
    queryFn: () => customerApi.getConsentHistory(customerId as string, { limit }),
    enabled: Boolean(customerId),
    staleTime: 60_000,
  });
}
