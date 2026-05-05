/**
 * Inbox API client (gap-16 v0).
 *
 * Backs ``GET /api/v1/inbox`` — read-only unified queue across the four
 * inbound source tables surfaced as a fourth queue card on ``/schedule``.
 */

import { apiClient } from '@/core/api/client';

export type InboxTriageStatus = 'pending' | 'handled' | 'dismissed';

export type InboxSourceTable =
  | 'job_confirmation_responses'
  | 'reschedule_requests'
  | 'campaign_responses'
  | 'communications'
  | 'consent';

export type InboxFilterToken =
  | 'all'
  | 'needs_triage'
  | 'orphans'
  | 'unrecognized'
  | 'opt_outs'
  | 'opt_ins'
  | 'archived';

export interface InboxItem {
  id: string;
  source_table: InboxSourceTable;
  triage_status: InboxTriageStatus;
  received_at: string;
  body: string;
  from_phone: string | null;
  customer_id: string | null;
  customer_name: string | null;
  appointment_id: string | null;
  parsed_keyword: string | null;
  status: string | null;
}

export interface InboxFilterCounts {
  all: number;
  needs_triage: number;
  orphans: number;
  unrecognized: number;
  opt_outs: number;
  opt_ins: number;
  archived: number;
}

export interface InboxListResponse {
  items: InboxItem[];
  next_cursor: string | null;
  has_more: boolean;
  counts: InboxFilterCounts;
}

export interface InboxListParams {
  triage?: InboxFilterToken;
  cursor?: string;
  limit?: number;
}

const BASE_URL = '/inbox';

export const inboxApi = {
  async list(params: InboxListParams = {}): Promise<InboxListResponse> {
    const response = await apiClient.get<InboxListResponse>(BASE_URL, {
      params,
    });
    return response.data;
  },
};
