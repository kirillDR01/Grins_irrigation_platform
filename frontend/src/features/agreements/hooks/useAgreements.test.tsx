import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  useAgreements,
  useAgreement,
  useAgreementMetrics,
  useRenewalPipeline,
  useFailedPayments,
  useMrrHistory,
  useTierDistribution,
  useAnnualNoticeDue,
  useOnboardingIncomplete,
  useAgreementCompliance,
  agreementKeys,
  tierKeys,
} from './useAgreements';
import { agreementsApi } from '../api/agreementsApi';
import type { Agreement, AgreementDetail, AgreementMetrics, MrrHistory, TierDistribution, DisclosureRecord } from '../types';

vi.mock('../api/agreementsApi', () => ({
  agreementsApi: {
    list: vi.fn(),
    get: vi.fn(),
    getMetrics: vi.fn(),
    getRenewalPipeline: vi.fn(),
    getFailedPayments: vi.fn(),
    getMrrHistory: vi.fn(),
    getTierDistribution: vi.fn(),
    getAnnualNoticeDue: vi.fn(),
    getCompliance: vi.fn(),
  },
}));

const createWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
};

const mockAgreement: Agreement = {
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
};

const mockDetail: AgreementDetail = {
  ...mockAgreement,
  stripe_subscription_id: 'sub_123',
  stripe_customer_id: 'cus_123',
  cancelled_at: null,
  cancellation_reason: null,
  cancellation_refund_amount: null,
  pause_reason: null,
  last_payment_date: '2026-01-01',
  last_payment_amount: 599,
  renewal_approved_by: null,
  renewal_approved_at: null,
  consent_recorded_at: '2026-01-01T00:00:00Z',
  consent_method: 'checkout',
  last_annual_notice_sent: null,
  last_renewal_notice_sent: null,
  notes: null,
  jobs: [],
  status_logs: [],
};

const mockPaginated = { items: [mockAgreement], total: 1, page: 1, page_size: 20, total_pages: 1 };

// ---- Key factories ----

describe('agreementKeys', () => {
  it('generates correct all key', () => {
    expect(agreementKeys.all).toEqual(['agreements']);
  });

  it('generates correct lists key', () => {
    expect(agreementKeys.lists()).toEqual(['agreements', 'list']);
  });

  it('generates correct list key with params', () => {
    const params = { page: 1, status: 'active' as const };
    expect(agreementKeys.list(params)).toEqual(['agreements', 'list', params]);
  });

  it('generates correct detail key', () => {
    expect(agreementKeys.detail('abc')).toEqual(['agreements', 'detail', 'abc']);
  });

  it('generates correct metrics key', () => {
    expect(agreementKeys.metrics()).toEqual(['agreements', 'metrics']);
  });

  it('generates correct renewalPipeline key', () => {
    expect(agreementKeys.renewalPipeline()).toEqual(['agreements', 'renewal-pipeline']);
  });

  it('generates correct failedPayments key', () => {
    expect(agreementKeys.failedPayments()).toEqual(['agreements', 'failed-payments']);
  });

  it('generates correct compliance key', () => {
    expect(agreementKeys.compliance('x')).toEqual(['agreements', 'compliance', 'x']);
  });
});

describe('tierKeys', () => {
  it('generates correct all key', () => {
    expect(tierKeys.all).toEqual(['agreement-tiers']);
  });

  it('generates correct detail key', () => {
    expect(tierKeys.detail('t1')).toEqual(['agreement-tiers', 'detail', 't1']);
  });
});

// ---- Query hooks ----

describe('useAgreements', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches agreements successfully', async () => {
    vi.mocked(agreementsApi.list).mockResolvedValue(mockPaginated);
    const { result } = renderHook(() => useAgreements(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockPaginated);
    expect(agreementsApi.list).toHaveBeenCalledWith(undefined);
  });

  it('passes params to API', async () => {
    vi.mocked(agreementsApi.list).mockResolvedValue(mockPaginated);
    const params = { page: 2, status: 'active' as const };
    const { result } = renderHook(() => useAgreements(params), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(agreementsApi.list).toHaveBeenCalledWith(params);
  });

  it('handles error', async () => {
    const err = new Error('fail');
    vi.mocked(agreementsApi.list).mockRejectedValue(err);
    const { result } = renderHook(() => useAgreements(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBe(err);
  });
});

describe('useAgreement', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches single agreement', async () => {
    vi.mocked(agreementsApi.get).mockResolvedValue(mockDetail);
    const { result } = renderHook(() => useAgreement('agr-1'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockDetail);
    expect(agreementsApi.get).toHaveBeenCalledWith('agr-1');
  });

  it('does not fetch when id is empty', () => {
    const { result } = renderHook(() => useAgreement(''), { wrapper: createWrapper() });
    expect(result.current.fetchStatus).toBe('idle');
    expect(agreementsApi.get).not.toHaveBeenCalled();
  });

  it('handles error', async () => {
    const err = new Error('not found');
    vi.mocked(agreementsApi.get).mockRejectedValue(err);
    const { result } = renderHook(() => useAgreement('bad'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBe(err);
  });
});

describe('useAgreementMetrics', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches metrics', async () => {
    const metrics: AgreementMetrics = {
      active_count: 10, mrr: 5000, arpa: 500, renewal_rate: 90, churn_rate: 5, past_due_amount: 200,
    };
    vi.mocked(agreementsApi.getMetrics).mockResolvedValue(metrics);
    const { result } = renderHook(() => useAgreementMetrics(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(metrics);
  });
});

describe('useRenewalPipeline', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches renewal pipeline', async () => {
    vi.mocked(agreementsApi.getRenewalPipeline).mockResolvedValue([mockAgreement]);
    const { result } = renderHook(() => useRenewalPipeline(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([mockAgreement]);
  });
});

describe('useFailedPayments', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches failed payments', async () => {
    vi.mocked(agreementsApi.getFailedPayments).mockResolvedValue([mockAgreement]);
    const { result } = renderHook(() => useFailedPayments(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([mockAgreement]);
  });
});

describe('useMrrHistory', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches MRR history', async () => {
    const history: MrrHistory = { data_points: [{ month: '2026-01', mrr: 5000 }] };
    vi.mocked(agreementsApi.getMrrHistory).mockResolvedValue(history);
    const { result } = renderHook(() => useMrrHistory(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(history);
  });
});

describe('useTierDistribution', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches tier distribution', async () => {
    const dist: TierDistribution = {
      items: [{ tier_id: 't1', tier_name: 'Pro', package_type: 'residential', active_count: 5 }],
    };
    vi.mocked(agreementsApi.getTierDistribution).mockResolvedValue(dist);
    const { result } = renderHook(() => useTierDistribution(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(dist);
  });
});

describe('useAnnualNoticeDue', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches annual notice due', async () => {
    vi.mocked(agreementsApi.getAnnualNoticeDue).mockResolvedValue([mockAgreement]);
    const { result } = renderHook(() => useAnnualNoticeDue(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([mockAgreement]);
  });
});

describe('useOnboardingIncomplete', () => {
  beforeEach(() => vi.clearAllMocks());

  it('filters agreements without property_id', async () => {
    const withProp = { ...mockAgreement, id: 'a1', property_id: 'p1' };
    const withoutProp = { ...mockAgreement, id: 'a2', property_id: null };
    vi.mocked(agreementsApi.list).mockResolvedValue({
      items: [withProp, withoutProp], total: 2, page: 1, page_size: 100, total_pages: 1,
    });
    const { result } = renderHook(() => useOnboardingIncomplete(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data![0].id).toBe('a2');
  });
});

describe('useAgreementCompliance', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches compliance records', async () => {
    const records: DisclosureRecord[] = [{
      id: 'd1', agreement_id: 'agr-1', customer_id: 'c1', disclosure_type: 'CONFIRMATION',
      sent_at: '2026-01-01T00:00:00Z', sent_via: 'email', recipient_email: 'a@b.com',
      recipient_phone: null, delivery_confirmed: true, created_at: '2026-01-01T00:00:00Z',
    }];
    vi.mocked(agreementsApi.getCompliance).mockResolvedValue(records);
    const { result } = renderHook(() => useAgreementCompliance('agr-1'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(records);
  });

  it('does not fetch when agreementId is empty', () => {
    const { result } = renderHook(() => useAgreementCompliance(''), { wrapper: createWrapper() });
    expect(result.current.fetchStatus).toBe('idle');
    expect(agreementsApi.getCompliance).not.toHaveBeenCalled();
  });
});
