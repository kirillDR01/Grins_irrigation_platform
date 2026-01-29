import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LienDeadlinesWidget } from './LienDeadlinesWidget';
import * as hooks from '../hooks';
import type { Invoice } from '../types';

// Mock the hooks module
vi.mock('../hooks', () => ({
  useLienDeadlines: vi.fn(),
}));

const mockInvoice45Day: Invoice = {
  id: 'inv-45-1',
  job_id: 'job-1',
  customer_id: 'cust-1',
  invoice_number: 'INV-2025-001',
  amount: 150.0,
  late_fee_amount: 0,
  total_amount: 150.0,
  invoice_date: '2025-01-01',
  due_date: '2025-01-15',
  status: 'overdue',
  payment_method: null,
  payment_reference: null,
  paid_at: null,
  paid_amount: null,
  reminder_count: 1,
  last_reminder_sent: null,
  lien_eligible: true,
  lien_warning_sent: null,
  lien_filed_date: null,
  line_items: null,
  notes: null,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

const mockInvoice120Day: Invoice = {
  id: 'inv-120-1',
  job_id: 'job-2',
  customer_id: 'cust-2',
  invoice_number: 'INV-2025-002',
  amount: 500.0,
  late_fee_amount: 25.0,
  total_amount: 525.0,
  invoice_date: '2024-10-01',
  due_date: '2024-10-15',
  status: 'lien_warning',
  payment_method: null,
  payment_reference: null,
  paid_at: null,
  paid_amount: null,
  reminder_count: 3,
  last_reminder_sent: '2024-12-01T00:00:00Z',
  lien_eligible: true,
  lien_warning_sent: '2024-11-15T00:00:00Z',
  lien_filed_date: null,
  line_items: null,
  notes: null,
  created_at: '2024-10-01T00:00:00Z',
  updated_at: '2024-12-01T00:00:00Z',
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    );
  };
}

describe('LienDeadlinesWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders widget container with correct data-testid', () => {
    vi.mocked(hooks.useLienDeadlines).mockReturnValue({
      data: { approaching_45_day: [], approaching_120_day: [] },
      isLoading: false,
      error: null,
    } as ReturnType<typeof hooks.useLienDeadlines>);

    render(<LienDeadlinesWidget />, { wrapper: createWrapper() });
    expect(screen.getByTestId('lien-deadlines-widget')).toBeInTheDocument();
  });

  it('displays loading state', () => {
    vi.mocked(hooks.useLienDeadlines).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as ReturnType<typeof hooks.useLienDeadlines>);

    render(<LienDeadlinesWidget />, { wrapper: createWrapper() });
    expect(screen.getByTestId('lien-deadlines-loading')).toBeInTheDocument();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('displays error state', () => {
    vi.mocked(hooks.useLienDeadlines).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to fetch'),
    } as ReturnType<typeof hooks.useLienDeadlines>);

    render(<LienDeadlinesWidget />, { wrapper: createWrapper() });
    expect(screen.getByTestId('lien-deadlines-error')).toBeInTheDocument();
    expect(screen.getByText('Failed to load lien deadlines')).toBeInTheDocument();
  });

  it('displays empty state when no deadlines', () => {
    vi.mocked(hooks.useLienDeadlines).mockReturnValue({
      data: { approaching_45_day: [], approaching_120_day: [] },
      isLoading: false,
      error: null,
    } as ReturnType<typeof hooks.useLienDeadlines>);

    render(<LienDeadlinesWidget />, { wrapper: createWrapper() });
    expect(screen.getByTestId('lien-deadlines-empty')).toBeInTheDocument();
    expect(screen.getByText('No approaching lien deadlines')).toBeInTheDocument();
  });

  it('displays 45-day warning invoices', () => {
    vi.mocked(hooks.useLienDeadlines).mockReturnValue({
      data: {
        approaching_45_day: [mockInvoice45Day],
        approaching_120_day: [],
      },
      isLoading: false,
      error: null,
    } as ReturnType<typeof hooks.useLienDeadlines>);

    render(<LienDeadlinesWidget />, { wrapper: createWrapper() });
    expect(screen.getByTestId('lien-deadlines-45-day-section')).toBeInTheDocument();
    expect(screen.getByText('45-Day Warning Due (1)')).toBeInTheDocument();
    expect(screen.getByText('INV-2025-001')).toBeInTheDocument();
    expect(screen.getByTestId('send-warning-btn-inv-45-1')).toBeInTheDocument();
  });

  it('displays 120-day filing invoices', () => {
    vi.mocked(hooks.useLienDeadlines).mockReturnValue({
      data: {
        approaching_45_day: [],
        approaching_120_day: [mockInvoice120Day],
      },
      isLoading: false,
      error: null,
    } as ReturnType<typeof hooks.useLienDeadlines>);

    render(<LienDeadlinesWidget />, { wrapper: createWrapper() });
    expect(screen.getByTestId('lien-deadlines-120-day-section')).toBeInTheDocument();
    expect(screen.getByText('120-Day Filing Due (1)')).toBeInTheDocument();
    expect(screen.getByText('INV-2025-002')).toBeInTheDocument();
    expect(screen.getByTestId('file-lien-btn-inv-120-1')).toBeInTheDocument();
  });

  it('displays both 45-day and 120-day sections when both have invoices', () => {
    vi.mocked(hooks.useLienDeadlines).mockReturnValue({
      data: {
        approaching_45_day: [mockInvoice45Day],
        approaching_120_day: [mockInvoice120Day],
      },
      isLoading: false,
      error: null,
    } as ReturnType<typeof hooks.useLienDeadlines>);

    render(<LienDeadlinesWidget />, { wrapper: createWrapper() });
    expect(screen.getByTestId('lien-deadlines-45-day-section')).toBeInTheDocument();
    expect(screen.getByTestId('lien-deadlines-120-day-section')).toBeInTheDocument();
  });

  it('shows "View all" link when more than 3 invoices in 45-day section', () => {
    const manyInvoices = Array.from({ length: 5 }, (_, i) => ({
      ...mockInvoice45Day,
      id: `inv-45-${i}`,
      invoice_number: `INV-2025-00${i}`,
    }));

    vi.mocked(hooks.useLienDeadlines).mockReturnValue({
      data: {
        approaching_45_day: manyInvoices,
        approaching_120_day: [],
      },
      isLoading: false,
      error: null,
    } as ReturnType<typeof hooks.useLienDeadlines>);

    render(<LienDeadlinesWidget />, { wrapper: createWrapper() });
    expect(screen.getByTestId('view-all-45-day-link')).toBeInTheDocument();
    expect(screen.getByText('View all 5 invoices')).toBeInTheDocument();
  });

  it('shows "View all" link when more than 3 invoices in 120-day section', () => {
    const manyInvoices = Array.from({ length: 4 }, (_, i) => ({
      ...mockInvoice120Day,
      id: `inv-120-${i}`,
      invoice_number: `INV-2024-00${i}`,
    }));

    vi.mocked(hooks.useLienDeadlines).mockReturnValue({
      data: {
        approaching_45_day: [],
        approaching_120_day: manyInvoices,
      },
      isLoading: false,
      error: null,
    } as ReturnType<typeof hooks.useLienDeadlines>);

    render(<LienDeadlinesWidget />, { wrapper: createWrapper() });
    expect(screen.getByTestId('view-all-120-day-link')).toBeInTheDocument();
    expect(screen.getByText('View all 4 invoices')).toBeInTheDocument();
  });

  it('renders invoice links correctly', () => {
    vi.mocked(hooks.useLienDeadlines).mockReturnValue({
      data: {
        approaching_45_day: [mockInvoice45Day],
        approaching_120_day: [],
      },
      isLoading: false,
      error: null,
    } as ReturnType<typeof hooks.useLienDeadlines>);

    render(<LienDeadlinesWidget />, { wrapper: createWrapper() });
    const link = screen.getByTestId('lien-deadline-link-inv-45-1');
    expect(link).toHaveAttribute('href', '/invoices/inv-45-1');
  });

  it('displays invoice status badge', () => {
    vi.mocked(hooks.useLienDeadlines).mockReturnValue({
      data: {
        approaching_45_day: [mockInvoice45Day],
        approaching_120_day: [],
      },
      isLoading: false,
      error: null,
    } as ReturnType<typeof hooks.useLienDeadlines>);

    render(<LienDeadlinesWidget />, { wrapper: createWrapper() });
    expect(screen.getByTestId('invoice-status-overdue')).toBeInTheDocument();
  });

  it('formats currency correctly', () => {
    vi.mocked(hooks.useLienDeadlines).mockReturnValue({
      data: {
        approaching_45_day: [mockInvoice45Day],
        approaching_120_day: [],
      },
      isLoading: false,
      error: null,
    } as ReturnType<typeof hooks.useLienDeadlines>);

    render(<LienDeadlinesWidget />, { wrapper: createWrapper() });
    expect(screen.getByText(/\$150\.00/)).toBeInTheDocument();
  });
});
