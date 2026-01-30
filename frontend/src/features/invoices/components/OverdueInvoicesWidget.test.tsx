import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { OverdueInvoicesWidget } from './OverdueInvoicesWidget';
import * as hooks from '../hooks';
import type { Invoice, PaginatedInvoiceResponse } from '../types';

// Mock the hooks
vi.mock('../hooks', () => ({
  useOverdueInvoices: vi.fn(),
}));

const mockInvoice: Invoice = {
  id: 'inv-1',
  job_id: 'job-1',
  customer_id: 'cust-1',
  invoice_number: 'INV-2025-001',
  amount: 150.0,
  late_fee_amount: 0,
  total_amount: 150.0,
  invoice_date: '2025-01-01',
  due_date: '2025-01-15',
  status: 'overdue',
  reminder_count: 0,
  lien_eligible: false,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{ui}</BrowserRouter>
    </QueryClientProvider>
  );
};

describe('OverdueInvoicesWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state', () => {
    vi.mocked(hooks.useOverdueInvoices).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as ReturnType<typeof hooks.useOverdueInvoices>);

    renderWithProviders(<OverdueInvoicesWidget />);

    expect(screen.getByTestId('overdue-invoices-widget')).toBeInTheDocument();
    expect(screen.getByTestId('overdue-invoices-loading')).toBeInTheDocument();
  });

  it('renders error state', () => {
    vi.mocked(hooks.useOverdueInvoices).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to load'),
    } as ReturnType<typeof hooks.useOverdueInvoices>);

    renderWithProviders(<OverdueInvoicesWidget />);

    expect(screen.getByTestId('overdue-invoices-error')).toBeInTheDocument();
    expect(screen.getByText('Failed to load overdue invoices')).toBeInTheDocument();
  });

  it('renders empty state when no overdue invoices', () => {
    const emptyResponse: PaginatedInvoiceResponse = {
      items: [],
      total: 0,
      page: 1,
      page_size: 5,
      total_pages: 0,
    };

    vi.mocked(hooks.useOverdueInvoices).mockReturnValue({
      data: emptyResponse,
      isLoading: false,
      error: null,
    } as ReturnType<typeof hooks.useOverdueInvoices>);

    renderWithProviders(<OverdueInvoicesWidget />);

    expect(screen.getByTestId('overdue-invoices-empty')).toBeInTheDocument();
    expect(screen.getByText('No overdue invoices')).toBeInTheDocument();
  });

  it('renders overdue invoices list', () => {
    const response: PaginatedInvoiceResponse = {
      items: [mockInvoice],
      total: 1,
      page: 1,
      page_size: 5,
      total_pages: 1,
    };

    vi.mocked(hooks.useOverdueInvoices).mockReturnValue({
      data: response,
      isLoading: false,
      error: null,
    } as ReturnType<typeof hooks.useOverdueInvoices>);

    const { container } = renderWithProviders(<OverdueInvoicesWidget />);

    expect(screen.getByTestId('overdue-invoice-item-inv-1')).toBeInTheDocument();
    expect(screen.getByText('INV-2025-001')).toBeInTheDocument();
    // Check for amount in the item (font-bold text-red-600)
    const amountElement = container.querySelector('.font-bold.text-red-600');
    expect(amountElement).toHaveTextContent('$150.00');
  });

  it('shows view all link when more than 5 invoices', () => {
    const response: PaginatedInvoiceResponse = {
      items: [mockInvoice],
      total: 10,
      page: 1,
      page_size: 5,
      total_pages: 2,
    };

    vi.mocked(hooks.useOverdueInvoices).mockReturnValue({
      data: response,
      isLoading: false,
      error: null,
    } as ReturnType<typeof hooks.useOverdueInvoices>);

    renderWithProviders(<OverdueInvoicesWidget />);

    expect(screen.getByTestId('view-all-overdue-link')).toBeInTheDocument();
    expect(screen.getByText('View all 10 overdue invoices')).toBeInTheDocument();
  });

  it('displays total amount in header', () => {
    const response: PaginatedInvoiceResponse = {
      items: [mockInvoice],
      total: 3,
      page: 1,
      page_size: 5,
      total_pages: 1,
    };

    vi.mocked(hooks.useOverdueInvoices).mockReturnValue({
      data: response,
      isLoading: false,
      error: null,
    } as ReturnType<typeof hooks.useOverdueInvoices>);

    const { container } = renderWithProviders(<OverdueInvoicesWidget />);

    // Check for total amount badge in header (bg-red-100 text-red-700)
    const badge = container.querySelector('.bg-red-100.text-red-700');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('$150.00');
  });

  it('has correct data-testid attributes', () => {
    const response: PaginatedInvoiceResponse = {
      items: [mockInvoice],
      total: 1,
      page: 1,
      page_size: 5,
      total_pages: 1,
    };

    vi.mocked(hooks.useOverdueInvoices).mockReturnValue({
      data: response,
      isLoading: false,
      error: null,
    } as ReturnType<typeof hooks.useOverdueInvoices>);

    renderWithProviders(<OverdueInvoicesWidget />);

    expect(screen.getByTestId('overdue-invoices-widget')).toBeInTheDocument();
    expect(screen.getByTestId('overdue-invoice-item-inv-1')).toBeInTheDocument();
    expect(screen.getByTestId('overdue-invoice-link-inv-1')).toBeInTheDocument();
    expect(screen.getByTestId('send-reminder-btn-inv-1')).toBeInTheDocument();
    expect(screen.getByTestId('view-overdue-btn-inv-1')).toBeInTheDocument();
  });
});
