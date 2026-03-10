import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { AgreementsList } from './AgreementsList';
import * as hooks from '../hooks/useAgreements';
import type { Agreement, AgreementStatus } from '../types';

vi.mock('../hooks/useAgreements', () => ({
  useAgreements: vi.fn(),
  agreementKeys: {
    all: ['agreements'],
    lists: () => ['agreements', 'list'],
    list: (p: unknown) => ['agreements', 'list', p],
    details: () => ['agreements', 'detail'],
    detail: (id: string) => ['agreements', 'detail', id],
  },
}));

const makeAgreement = (overrides: Partial<Agreement> = {}): Agreement => ({
  id: '1',
  agreement_number: 'AGR-2026-001',
  customer_id: 'c1',
  customer_name: 'John Doe',
  tier_id: 't1',
  tier_name: 'Professional',
  package_type: 'residential',
  property_id: 'p1',
  status: 'active',
  annual_price: 599,
  start_date: '2026-03-01',
  end_date: '2027-03-01',
  renewal_date: '2027-03-01',
  auto_renew: true,
  payment_status: 'current',
  created_at: '2026-03-01T00:00:00Z',
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

describe('AgreementsList', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders loading state', () => {
    vi.mocked(hooks.useAgreements).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof hooks.useAgreements>);

    render(<AgreementsList />, { wrapper });
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders error state', () => {
    vi.mocked(hooks.useAgreements).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof hooks.useAgreements>);

    render(<AgreementsList />, { wrapper });
    expect(screen.getByTestId('error-message')).toBeInTheDocument();
  });

  it('renders empty state', async () => {
    vi.mocked(hooks.useAgreements).mockReturnValue({
      data: { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof hooks.useAgreements>);

    render(<AgreementsList />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('agreements-list')).toBeInTheDocument();
    });
    expect(screen.getByText(/no agreements found/i)).toBeInTheDocument();
  });

  it('renders table with agreements', async () => {
    const items = [
      makeAgreement(),
      makeAgreement({ id: '2', agreement_number: 'AGR-2026-002', customer_name: 'Jane Smith', status: 'pending' }),
    ];
    vi.mocked(hooks.useAgreements).mockReturnValue({
      data: { items, total: 2, page: 1, page_size: 20, total_pages: 1 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof hooks.useAgreements>);

    render(<AgreementsList />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('agreements-table')).toBeInTheDocument();
    });
    expect(screen.getByText('AGR-2026-001')).toBeInTheDocument();
    expect(screen.getByText('AGR-2026-002')).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
    expect(screen.getAllByTestId('agreement-row')).toHaveLength(2);
  });

  it('renders status filter tabs', async () => {
    vi.mocked(hooks.useAgreements).mockReturnValue({
      data: { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof hooks.useAgreements>);

    render(<AgreementsList />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('agreement-status-tabs')).toBeInTheDocument();
    });
    const tabs: Array<{ label: string; value: string }> = [
      { label: 'All', value: 'all' },
      { label: 'Active', value: 'active' },
      { label: 'Pending', value: 'pending' },
      { label: 'Cancelled', value: 'cancelled' },
    ];
    for (const t of tabs) {
      expect(screen.getByTestId(`tab-${t.value}`)).toBeInTheDocument();
    }
  });

  it('clicking a status tab calls useAgreements with correct params', async () => {
    const user = userEvent.setup();
    vi.mocked(hooks.useAgreements).mockReturnValue({
      data: { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof hooks.useAgreements>);

    render(<AgreementsList />, { wrapper });
    await user.click(screen.getByTestId('tab-active'));

    // After clicking, useAgreements should have been called with status: 'active'
    const lastCall = vi.mocked(hooks.useAgreements).mock.calls.at(-1);
    expect(lastCall?.[0]).toMatchObject({ status: 'active', page: 1 });
  });

  it('renders pagination when multiple pages', async () => {
    vi.mocked(hooks.useAgreements).mockReturnValue({
      data: { items: [makeAgreement()], total: 40, page: 1, page_size: 20, total_pages: 2 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof hooks.useAgreements>);

    render(<AgreementsList />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('pagination')).toBeInTheDocument();
    });
    expect(screen.getByTestId('pagination-prev')).toBeDisabled();
    expect(screen.getByTestId('pagination-next')).toBeEnabled();
  });

  it('renders status badges', async () => {
    const items = [
      makeAgreement({ status: 'active' }),
      makeAgreement({ id: '2', status: 'past_due' as AgreementStatus }),
    ];
    vi.mocked(hooks.useAgreements).mockReturnValue({
      data: { items, total: 2, page: 1, page_size: 20, total_pages: 1 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof hooks.useAgreements>);

    render(<AgreementsList />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('status-active')).toBeInTheDocument();
    });
    expect(screen.getByTestId('status-past_due')).toBeInTheDocument();
  });
});
