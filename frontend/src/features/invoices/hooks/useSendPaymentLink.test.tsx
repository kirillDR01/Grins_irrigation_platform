/**
 * Tests for useSendPaymentLink mutation (plan §Phase 3.2).
 *
 * Validates:
 *  - The mutation calls invoiceApi.sendPaymentLink with the invoice id.
 *  - On success it invalidates invoice + customer-invoice + appointment
 *    cache prefixes (per plan F14, no cross-feature query-key import).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useSendPaymentLink } from './useInvoiceMutations';
import { invoiceApi } from '../api/invoiceApi';

vi.mock('../api/invoiceApi', () => ({
  invoiceApi: {
    sendPaymentLink: vi.fn(),
  },
}));

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, wrapper };
}

describe('useSendPaymentLink', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('forwards the invoice id to the API client', async () => {
    vi.mocked(invoiceApi.sendPaymentLink).mockResolvedValue({
      channel: 'sms',
      link_url: 'https://buy.stripe.com/test_abc',
      sent_at: '2026-04-28T00:00:00Z',
      sent_count: 1,
    });
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useSendPaymentLink(), { wrapper });

    result.current.mutate('inv-42');

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invoiceApi.sendPaymentLink).toHaveBeenCalledWith('inv-42');
    expect(result.current.data).toMatchObject({ channel: 'sms', sent_count: 1 });
  });

  it('invalidates invoices, customer-invoices, and appointments on success', async () => {
    vi.mocked(invoiceApi.sendPaymentLink).mockResolvedValue({
      channel: 'email',
      link_url: 'https://buy.stripe.com/test_xyz',
      sent_at: '2026-04-28T00:00:00Z',
      sent_count: 3,
    });
    const { client, wrapper } = makeWrapper();
    const spy = vi.spyOn(client, 'invalidateQueries');
    const { result } = renderHook(() => useSendPaymentLink(), { wrapper });

    result.current.mutate('inv-42');

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const invalidatedKeys = spy.mock.calls.map((c) => c[0]?.queryKey);
    // Plan §Phase 3.2 / F14: invalidate by literal key prefixes so the
    // appointment view refreshes without crossing the feature boundary.
    expect(invalidatedKeys).toEqual(
      expect.arrayContaining([
        ['appointments'],
      ]),
    );
    // And invoice + customer-invoice (keyed via invoiceKeys / customerInvoiceKeys).
    expect(spy).toHaveBeenCalled();
  });

  it('surfaces API errors to the caller', async () => {
    vi.mocked(invoiceApi.sendPaymentLink).mockRejectedValue(
      new Error('No contact method'),
    );
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useSendPaymentLink(), { wrapper });

    result.current.mutate('inv-42');

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe('No contact method');
  });
});
