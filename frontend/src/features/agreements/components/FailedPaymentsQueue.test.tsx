import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { FailedPaymentsQueue } from './FailedPaymentsQueue';
import * as hooks from '../hooks/useAgreements';
import * as mutationHooks from '../hooks/useAgreementMutations';
import type { Agreement } from '../types';

vi.mock('../hooks/useAgreements', () => ({
  useFailedPayments: vi.fn(),
  agreementKeys: {
    all: ['agreements'],
    lists: () => ['agreements', 'list'],
    list: (p: unknown) => ['agreements', 'list', p],
    details: () => ['agreements', 'detail'],
    detail: (id: string) => ['agreements', 'detail', id],
    metrics: () => ['agreements', 'metrics'],
    renewalPipeline: () => ['agreements', 'renewal-pipeline'],
    failedPayments: () => ['agreements', 'failed-payments'],
  },
}));

vi.mock('../hooks/useAgreementMutations', () => ({
  useUpdateAgreementStatus: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const makeFailedAgreement = (overrides: Partial<Agreement> = {}): Agreement => ({
  id: 'f1',
  agreement_number: 'AGR-2026-020',
  customer_id: 'c2',
  customer_name: 'Bob Failed',
  tier_id: 't1',
  tier_name: 'Essential',
  package_type: 'residential',
  property_id: 'p1',
  status: 'past_due',
  annual_price: 399,
  start_date: '2025-03-01',
  end_date: '2026-03-01',
  renewal_date: '2026-03-01',
  auto_renew: true,
  payment_status: 'past_due',
  created_at: '2025-03-01T00:00:00Z',
  ...overrides,
});

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}

describe('FailedPaymentsQueue', () => {
  const mockUpdateStatus = { mutateAsync: vi.fn(), isPending: false };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(mutationHooks.useUpdateAgreementStatus).mockReturnValue(mockUpdateStatus as unknown as ReturnType<typeof mutationHooks.useUpdateAgreementStatus>);
  });

  it('renders empty state', () => {
    vi.mocked(hooks.useFailedPayments).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useFailedPayments>);

    render(<FailedPaymentsQueue />, { wrapper });
    expect(screen.getByText(/no failed payments/i)).toBeInTheDocument();
  });

  it('renders agreements with resume/cancel buttons', () => {
    vi.mocked(hooks.useFailedPayments).mockReturnValue({
      data: [makeFailedAgreement()],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useFailedPayments>);

    render(<FailedPaymentsQueue />, { wrapper });
    expect(screen.getByTestId('failed-payment-row-f1')).toBeInTheDocument();
    expect(screen.getByTestId('resume-payment-f1')).toBeInTheDocument();
    expect(screen.getByTestId('cancel-payment-f1')).toBeInTheDocument();
    expect(screen.getByText('AGR-2026-020')).toBeInTheDocument();
  });

  it('calls resume (active status) on click', async () => {
    const user = userEvent.setup();
    mockUpdateStatus.mutateAsync.mockResolvedValue({});
    vi.mocked(hooks.useFailedPayments).mockReturnValue({
      data: [makeFailedAgreement()],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useFailedPayments>);

    render(<FailedPaymentsQueue />, { wrapper });
    await user.click(screen.getByTestId('resume-payment-f1'));
    expect(mockUpdateStatus.mutateAsync).toHaveBeenCalledWith({
      id: 'f1',
      data: { status: 'active', reason: 'Payment recovered' },
    });
  });

  it('calls cancel on click', async () => {
    const user = userEvent.setup();
    mockUpdateStatus.mutateAsync.mockResolvedValue({});
    vi.mocked(hooks.useFailedPayments).mockReturnValue({
      data: [makeFailedAgreement()],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useFailedPayments>);

    render(<FailedPaymentsQueue />, { wrapper });
    await user.click(screen.getByTestId('cancel-payment-f1'));
    expect(mockUpdateStatus.mutateAsync).toHaveBeenCalledWith({
      id: 'f1',
      data: { status: 'cancelled', reason: 'Payment failure' },
    });
  });

  it('renders error state', () => {
    vi.mocked(hooks.useFailedPayments).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('fail'),
    } as unknown as ReturnType<typeof hooks.useFailedPayments>);

    render(<FailedPaymentsQueue />, { wrapper });
    expect(screen.getByText(/failed to load failed payments/i)).toBeInTheDocument();
  });
});
