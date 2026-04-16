import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('../api/invoiceApi', () => ({
  invoiceApi: {
    lienCandidates: vi.fn(),
    sendLienNotice: vi.fn(),
  },
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { invoiceApi } from '../api/invoiceApi';
import { useLienCandidates, useSendLienNotice } from './useLienReview';
import { invoiceKeys } from './useInvoices';
import type { LienCandidate } from '../types';

function createWrapper(client: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

function makeClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

describe('useLienCandidates (CR-5)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches and returns array of candidates', async () => {
    const candidates: LienCandidate[] = [
      {
        customer_id: 'c1',
        customer_name: 'Alice',
        customer_phone: '+19527373312',
        oldest_invoice_age_days: 90,
        total_past_due_amount: '800.00',
        invoice_ids: ['inv-1'],
        invoice_numbers: ['INV-1'],
      },
    ];
    vi.mocked(invoiceApi.lienCandidates).mockResolvedValue(candidates);

    const client = makeClient();
    const { result } = renderHook(() => useLienCandidates(), {
      wrapper: createWrapper(client),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    expect(result.current.data).toEqual(candidates);
    expect(invoiceApi.lienCandidates).toHaveBeenCalledTimes(1);
  });
});

describe('useSendLienNotice (CR-5)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('invalidates lien-candidates query on success', async () => {
    vi.mocked(invoiceApi.sendLienNotice).mockResolvedValue({
      success: true,
      customer_id: 'c1',
      sent_at: '2026-04-16T12:00:00Z',
      sms_message_id: 'msg-1',
      message: 'sent',
    });

    const client = makeClient();
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries');

    const { result } = renderHook(() => useSendLienNotice(), {
      wrapper: createWrapper(client),
    });

    await result.current.mutateAsync('c1');

    // invoiceKeys.lienCandidates() is included in the invalidation set.
    const invalidatedKeys = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
    const expectedKey = invoiceKeys.lienCandidates();
    const wasInvalidated = invalidatedKeys.some(
      (k) => JSON.stringify(k) === JSON.stringify(expectedKey),
    );
    expect(wasInvalidated).toBe(true);
  });
});
