import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { RenewalPipelineQueue } from './RenewalPipelineQueue';
import * as hooks from '../hooks/useAgreements';
import * as mutationHooks from '../hooks/useAgreementMutations';
import type { Agreement } from '../types';

vi.mock('../hooks/useAgreements', () => ({
  useRenewalPipeline: vi.fn(),
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
  useApproveRenewal: vi.fn(),
  useRejectRenewal: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const makeRenewalAgreement = (overrides: Partial<Agreement> = {}): Agreement => ({
  id: 'r1',
  agreement_number: 'AGR-2026-010',
  customer_id: 'c1',
  customer_name: 'Alice Renewal',
  tier_id: 't1',
  tier_name: 'Professional',
  package_type: 'residential',
  property_id: 'p1',
  status: 'pending_renewal',
  annual_price: 599,
  start_date: '2025-03-01',
  end_date: '2026-03-01',
  renewal_date: new Date(Date.now() + 5 * 86400000).toISOString().split('T')[0],
  auto_renew: true,
  payment_status: 'current',
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

describe('RenewalPipelineQueue', () => {
  const mockApprove = { mutateAsync: vi.fn(), isPending: false };
  const mockReject = { mutateAsync: vi.fn(), isPending: false };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(mutationHooks.useApproveRenewal).mockReturnValue(mockApprove as unknown as ReturnType<typeof mutationHooks.useApproveRenewal>);
    vi.mocked(mutationHooks.useRejectRenewal).mockReturnValue(mockReject as unknown as ReturnType<typeof mutationHooks.useRejectRenewal>);
  });

  it('renders loading state', () => {
    vi.mocked(hooks.useRenewalPipeline).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof hooks.useRenewalPipeline>);

    render(<RenewalPipelineQueue />, { wrapper });
    expect(screen.getByTestId('renewal-pipeline-queue')).toBeInTheDocument();
  });

  it('renders empty state', () => {
    vi.mocked(hooks.useRenewalPipeline).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useRenewalPipeline>);

    render(<RenewalPipelineQueue />, { wrapper });
    expect(screen.getByText(/no pending renewals/i)).toBeInTheDocument();
  });

  it('renders agreements with approve/reject buttons', () => {
    vi.mocked(hooks.useRenewalPipeline).mockReturnValue({
      data: [makeRenewalAgreement()],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useRenewalPipeline>);

    render(<RenewalPipelineQueue />, { wrapper });
    expect(screen.getByTestId('renewal-row-r1')).toBeInTheDocument();
    expect(screen.getByTestId('approve-renewal-r1')).toBeInTheDocument();
    expect(screen.getByTestId('reject-renewal-r1')).toBeInTheDocument();
    expect(screen.getByText('AGR-2026-010')).toBeInTheDocument();
  });

  it('calls approve mutation on click', async () => {
    const user = userEvent.setup();
    mockApprove.mutateAsync.mockResolvedValue({});
    vi.mocked(hooks.useRenewalPipeline).mockReturnValue({
      data: [makeRenewalAgreement()],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useRenewalPipeline>);

    render(<RenewalPipelineQueue />, { wrapper });
    await user.click(screen.getByTestId('approve-renewal-r1'));
    expect(mockApprove.mutateAsync).toHaveBeenCalledWith('r1');
  });

  it('calls reject mutation on click', async () => {
    const user = userEvent.setup();
    mockReject.mutateAsync.mockResolvedValue({});
    vi.mocked(hooks.useRenewalPipeline).mockReturnValue({
      data: [makeRenewalAgreement()],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useRenewalPipeline>);

    render(<RenewalPipelineQueue />, { wrapper });
    await user.click(screen.getByTestId('reject-renewal-r1'));
    expect(mockReject.mutateAsync).toHaveBeenCalledWith({ id: 'r1' });
  });

  it('shows urgency warning for renewal within 7 days', () => {
    const inFiveDays = new Date(Date.now() + 5 * 86400000).toISOString().split('T')[0];
    vi.mocked(hooks.useRenewalPipeline).mockReturnValue({
      data: [makeRenewalAgreement({ renewal_date: inFiveDays })],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useRenewalPipeline>);

    render(<RenewalPipelineQueue />, { wrapper });
    expect(screen.getByTestId('urgency-warning')).toBeInTheDocument();
  });

  it('shows urgency critical for renewal within 1 day', () => {
    const tomorrow = new Date(Date.now() + 0.5 * 86400000).toISOString().split('T')[0];
    vi.mocked(hooks.useRenewalPipeline).mockReturnValue({
      data: [makeRenewalAgreement({ renewal_date: tomorrow })],
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useRenewalPipeline>);

    render(<RenewalPipelineQueue />, { wrapper });
    expect(screen.getByTestId('urgency-critical')).toBeInTheDocument();
  });
});
