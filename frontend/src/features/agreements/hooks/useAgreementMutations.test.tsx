import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  useUpdateAgreementStatus,
  useApproveRenewal,
  useRejectRenewal,
  useUpdateNotes,
} from './useAgreementMutations';
import { agreementsApi } from '../api/agreementsApi';
import type { AgreementDetail } from '../types';

vi.mock('../api/agreementsApi', () => ({
  agreementsApi: {
    updateStatus: vi.fn(),
    approveRenewal: vi.fn(),
    rejectRenewal: vi.fn(),
    updateNotes: vi.fn(),
  },
}));

const createWrapper = () => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
};

const mockDetail: AgreementDetail = {
  id: 'agr-1',
  agreement_number: 'AGR-2026-001',
  customer_id: 'cust-1',
  customer_name: 'John Doe',
  tier_id: 'tier-1',
  tier_name: 'Professional',
  package_type: 'residential',
  property_id: 'prop-1',
  status: 'active',
  annual_price: 599,
  start_date: '2026-01-01',
  end_date: '2026-12-31',
  renewal_date: '2026-12-31',
  auto_renew: true,
  payment_status: 'current',
  created_at: '2026-01-01T00:00:00Z',
  stripe_subscription_id: null,
  stripe_customer_id: null,
  cancelled_at: null,
  cancellation_reason: null,
  cancellation_refund_amount: null,
  pause_reason: null,
  last_payment_date: null,
  last_payment_amount: null,
  renewal_approved_by: null,
  renewal_approved_at: null,
  consent_recorded_at: null,
  consent_method: null,
  last_annual_notice_sent: null,
  last_renewal_notice_sent: null,
  notes: null,
  jobs: [],
  status_logs: [],
};

describe('useUpdateAgreementStatus', () => {
  beforeEach(() => vi.clearAllMocks());

  it('updates status successfully', async () => {
    const updated = { ...mockDetail, status: 'paused' as const };
    vi.mocked(agreementsApi.updateStatus).mockResolvedValue(updated);

    const { result } = renderHook(() => useUpdateAgreementStatus(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ id: 'agr-1', data: { status: 'paused', reason: 'test' } });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(agreementsApi.updateStatus).toHaveBeenCalledWith('agr-1', { status: 'paused', reason: 'test' });
  });

  it('handles error', async () => {
    const err = new Error('invalid transition');
    vi.mocked(agreementsApi.updateStatus).mockRejectedValue(err);

    const { result } = renderHook(() => useUpdateAgreementStatus(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ id: 'agr-1', data: { status: 'active' } });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBe(err);
  });
});

describe('useApproveRenewal', () => {
  beforeEach(() => vi.clearAllMocks());

  it('approves renewal successfully', async () => {
    vi.mocked(agreementsApi.approveRenewal).mockResolvedValue(mockDetail);

    const { result } = renderHook(() => useApproveRenewal(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate('agr-1');
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(agreementsApi.approveRenewal).toHaveBeenCalledWith('agr-1');
  });

  it('handles error', async () => {
    const err = new Error('not pending renewal');
    vi.mocked(agreementsApi.approveRenewal).mockRejectedValue(err);

    const { result } = renderHook(() => useApproveRenewal(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate('agr-1');
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBe(err);
  });
});

describe('useRejectRenewal', () => {
  beforeEach(() => vi.clearAllMocks());

  it('rejects renewal successfully', async () => {
    vi.mocked(agreementsApi.rejectRenewal).mockResolvedValue(mockDetail);

    const { result } = renderHook(() => useRejectRenewal(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ id: 'agr-1', data: { reason: 'customer request' } });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(agreementsApi.rejectRenewal).toHaveBeenCalledWith('agr-1', { reason: 'customer request' });
  });

  it('rejects renewal without reason', async () => {
    vi.mocked(agreementsApi.rejectRenewal).mockResolvedValue(mockDetail);

    const { result } = renderHook(() => useRejectRenewal(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ id: 'agr-1' });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(agreementsApi.rejectRenewal).toHaveBeenCalledWith('agr-1', undefined);
  });

  it('handles error', async () => {
    const err = new Error('fail');
    vi.mocked(agreementsApi.rejectRenewal).mockRejectedValue(err);

    const { result } = renderHook(() => useRejectRenewal(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ id: 'agr-1' });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBe(err);
  });
});

describe('useUpdateNotes', () => {
  beforeEach(() => vi.clearAllMocks());

  it('updates notes successfully', async () => {
    const updated = { ...mockDetail, notes: 'new note' };
    vi.mocked(agreementsApi.updateNotes).mockResolvedValue(updated);

    const { result } = renderHook(() => useUpdateNotes(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ id: 'agr-1', notes: 'new note' });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(agreementsApi.updateNotes).toHaveBeenCalledWith('agr-1', 'new note');
  });

  it('clears notes with null', async () => {
    const updated = { ...mockDetail, notes: null };
    vi.mocked(agreementsApi.updateNotes).mockResolvedValue(updated);

    const { result } = renderHook(() => useUpdateNotes(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ id: 'agr-1', notes: null });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(agreementsApi.updateNotes).toHaveBeenCalledWith('agr-1', null);
  });

  it('handles error', async () => {
    const err = new Error('fail');
    vi.mocked(agreementsApi.updateNotes).mockRejectedValue(err);

    const { result } = renderHook(() => useUpdateNotes(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate({ id: 'agr-1', notes: 'x' });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBe(err);
  });
});
