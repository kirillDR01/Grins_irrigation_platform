/**
 * useCustomerConversation — paginated conversation hook (gap-13).
 *
 * Backed by ``GET /api/v1/customers/{id}/conversation`` which UNIONs
 * sent_messages + job_confirmation_responses + campaign_responses +
 * communications into a single chronological stream.
 *
 * Mirrors the 60 s polling cadence of ``useCustomerSentMessages`` so
 * inbound replies show up in the per-customer Messages tab without a
 * manual refresh.
 */

import { useInfiniteQuery } from '@tanstack/react-query';
import { customerApi } from '../api/customerApi';
import { customerKeys } from './useCustomers';
import type { ConversationResponse } from '../types';

const PAGE_SIZE = 50;

export function useCustomerConversation(customerId: string) {
  return useInfiniteQuery<
    ConversationResponse,
    Error,
    { pages: ConversationResponse[]; pageParams: (string | null)[] },
    readonly unknown[],
    string | null
  >({
    queryKey: customerKeys.conversation(customerId),
    queryFn: ({ pageParam }) =>
      customerApi.getConversation(customerId, {
        cursor: pageParam ?? undefined,
        limit: PAGE_SIZE,
      }),
    initialPageParam: null,
    getNextPageParam: (lastPage) =>
      lastPage.has_more ? lastPage.next_cursor : null,
    enabled: !!customerId,
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });
}
