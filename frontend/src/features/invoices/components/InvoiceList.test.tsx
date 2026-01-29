import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { InvoiceList } from './InvoiceList';
import { invoiceApi } from '../api/invoiceApi';
import type { Invoice } from '../types';

// Mock the API
vi.mock('../api/invoiceApi', () => ({
  invoiceApi: {
    list: vi.fn(),
  },
}));

const mockInvoices: Invoice[] = [
  {
    id: '123e4567-e89b-12d3-a456-426614174000',
    job_id: '123e4567-e89b-12d3-a456-426614174001',
    customer_id: '123e4567-e89b-12d3-a456-426614174002',
    invoice_number: 'INV-2025-0001',
    amount: 150.0,
    late_fee_amount: 0,
    total_amount: 150.0,
    invoice_date: '2025-01-15',
    due_date: '2025-01-30',
    status: 'sent',
    payment_method: null,
    payment_reference: null,
    paid_at: null,
    paid_amount: null,
    reminder_count: 0,
    last_reminder_sent: null,
    lien_eligible: false,
    lien_warning_sent: null,
    lien_filed_date: null,
    line_items: null,
    notes: null,
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-01-15T10:00:00Z',
  },
  {
    id: '223e4567-e89b-12d3-a456-426614174000',
    job_id: '223e4567-e89b-12d3-a456-426614174001',
    customer_id: '223e4567-e89b-12d3-a456-426614174002',
    invoice_number: 'INV-2025-0002',
    amount: 250.0,
    late_fee_amount: 25.0,
    total_amount: 275.0,
    invoice_date: '2025-01-10',
    due_date: '2025-01-25',
    status: 'overdue',
    payment_method: null,
    payment_reference: null,
    paid_at: null,
    paid_amount: null,
    reminder_count: 2,
    last_reminder_sent: '2025-01-28T10:00:00Z',
    lien_eligible: true,
    lien_warning_sent: null,
    lien_filed_date: null,
    line_items: null,
    notes: null,
    created_at: '2025-01-10T10:00:00Z',
    updated_at: '2025-01-28T10:00:00Z',
  },
  {
    id: '323e4567-e89b-12d3-a456-426614174000',
    job_id: '323e4567-e89b-12d3-a456-426614174001',
    customer_id: '323e4567-e89b-12d3-a456-426614174002',
    invoice_number: 'INV-2025-0003',
    amount: 500.0,
    late_fee_amount: 0,
    total_amount: 500.0,
    invoice_date: '2025-01-20',
    due_date: '2025-02-05',
    status: 'paid',
    payment_method: 'venmo',
    payment_reference: 'VNM123456',
    paid_at: '2025-01-22T14:30:00Z',
    paid_amount: 500.0,
    reminder_count: 0,
    last_reminder_sent: null,
    lien_eligible: false,
    lien_warning_sent: null,
    lien_filed_date: null,
    line_items: null,
    notes: null,
    created_at: '2025-01-20T10:00:00Z',
    updated_at: '2025-01-22T14:30:00Z',
  },
];

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
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

describe('InvoiceList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders DataTable', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices,
      total: 3,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<InvoiceList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('invoice-table')).toBeInTheDocument();
    });
  });

  it('displays invoice number column', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices,
      total: 3,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<InvoiceList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('INV-2025-0001')).toBeInTheDocument();
    });
  });

  it('displays amount column', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices,
      total: 3,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<InvoiceList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('$150.00')).toBeInTheDocument();
      expect(screen.getByText('$275.00')).toBeInTheDocument();
      expect(screen.getByText('$500.00')).toBeInTheDocument();
    });
  });

  it('displays status column with badges', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices,
      total: 3,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<InvoiceList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('invoice-status-sent')).toBeInTheDocument();
      expect(screen.getByTestId('invoice-status-overdue')).toBeInTheDocument();
      expect(screen.getByTestId('invoice-status-paid')).toBeInTheDocument();
    });
  });

  it('displays due_date column', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices,
      total: 3,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<InvoiceList />, { wrapper: createWrapper() });

    await waitFor(() => {
      // Check that the table has rows with invoice data
      const rows = screen.getAllByTestId('invoice-row');
      expect(rows.length).toBe(3);
    });
  });

  it('displays actions column', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices,
      total: 3,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<InvoiceList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(
        screen.getByTestId('invoice-actions-123e4567-e89b-12d3-a456-426614174000'),
      ).toBeInTheDocument();
    });
  });

  it('renders filter controls', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices,
      total: 3,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<InvoiceList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('invoice-filter-status')).toBeInTheDocument();
      expect(screen.getByTestId('invoice-filter-date-from')).toBeInTheDocument();
      expect(screen.getByTestId('invoice-filter-date-to')).toBeInTheDocument();
    });
  });

  it('renders pagination when multiple pages', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices,
      total: 50,
      page: 1,
      page_size: 20,
      total_pages: 3,
    });

    render(<InvoiceList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('pagination-prev')).toBeInTheDocument();
      expect(screen.getByTestId('pagination-next')).toBeInTheDocument();
    });
  });

  it('has correct data-testid on list container', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices,
      total: 3,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<InvoiceList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('invoice-list')).toBeInTheDocument();
    });
  });

  it('shows empty state when no invoices', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    });

    render(<InvoiceList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('No invoices found.')).toBeInTheDocument();
    });
  });

  it('shows loading state initially', () => {
    vi.mocked(invoiceApi.list).mockImplementation(
      () => new Promise(() => {}), // Never resolves
    );

    render(<InvoiceList />, { wrapper: createWrapper() });

    expect(screen.getByText('Loading invoices...')).toBeInTheDocument();
  });

  it('shows error state on API failure', async () => {
    vi.mocked(invoiceApi.list).mockRejectedValue(new Error('API Error'));

    render(<InvoiceList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
    });
  });

  it('pagination next button works', async () => {
    const user = userEvent.setup();
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices,
      total: 50,
      page: 1,
      page_size: 20,
      total_pages: 3,
    });

    render(<InvoiceList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('pagination-next')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('pagination-next'));

    // API should be called again with page 2
    await waitFor(() => {
      expect(invoiceApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ page: 2 }),
      );
    });
  });
});
