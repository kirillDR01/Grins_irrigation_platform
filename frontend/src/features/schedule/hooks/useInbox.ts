/**
 * useInbox — paginated unified inbox hook (gap-16 v0).
 *
 * Backed by ``GET /api/v1/inbox``. Mirrors the polling cadence (60 s) of
 * the sibling NoReplyReviewQueue / RescheduleRequestsQueue so the new
 * fourth queue card stays fresh under the same SLO.
 */

import { useInfiniteQuery } from '@tanstack/react-query';
import {
  inboxApi,
  type InboxFilterToken,
  type InboxListResponse,
} from '../api/inboxApi';

export const inboxKeys = {
  all: ['schedule', 'inbox'] as const,
  list: (filter: InboxFilterToken) =>
    [...inboxKeys.all, 'list', filter] as const,
};

const PAGE_SIZE = 50;

export function useInbox(filter: InboxFilterToken = 'all') {
  return useInfiniteQuery<
    InboxListResponse,
    Error,
    { pages: InboxListResponse[]; pageParams: (string | null)[] },
    readonly unknown[],
    string | null
  >({
    queryKey: inboxKeys.list(filter),
    queryFn: ({ pageParam }) =>
      inboxApi.list({
        triage: filter,
        cursor: pageParam ?? undefined,
        limit: PAGE_SIZE,
      }),
    initialPageParam: null,
    getNextPageParam: (lastPage) =>
      lastPage.has_more ? lastPage.next_cursor : null,
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });
}
