import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { InvoiceList } from './InvoiceList';
import { invoiceApi } from '../api/invoiceApi';
import type { Invoice } from '../types';

// Mock the API
vi.mock('../api/invoiceApi', () => ({
  invoiceApi: {
    list: vi.fn(),
    massNotify: vi.fn(),
    bulkNotify: vi.fn(),
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
    customer_name: 'John Doe',
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
    customer_name: 'Jane Smith',
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
    customer_name: 'Bob Wilson',
    created_at: '2025-01-20T10:00:00Z',
    updated_at: '2025-01-22T14:30:00Z',
  },
  {
    id: '423e4567-e89b-12d3-a456-426614174000',
    job_id: '423e4567-e89b-12d3-a456-426614174001',
    customer_id: '423e4567-e89b-12d3-a456-426614174002',
    invoice_number: 'INV-2025-0004',
    amount: 300.0,
    late_fee_amount: 0,
    total_amount: 300.0,
    invoice_date: '2025-02-01',
    due_date: '2025-02-15',
    status: 'paid',
    payment_method: 'credit_card',
    payment_reference: 'stripe:pi_3OabcXYZ123456789',
    paid_at: '2025-02-03T11:00:00Z',
    paid_amount: 300.0,
    reminder_count: 0,
    last_reminder_sent: null,
    lien_eligible: false,
    lien_warning_sent: null,
    lien_filed_date: null,
    line_items: null,
    notes: null,
    customer_name: 'Alice Tester',
    created_at: '2025-02-01T10:00:00Z',
    updated_at: '2025-02-03T11:00:00Z',
  },
];

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
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
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
      writable: true,
      configurable: true,
    });
  });

  it('renders DataTable', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices, total: 4, page: 1, page_size: 20, total_pages: 1,
    });
    render(<InvoiceList />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('invoice-table')).toBeInTheDocument();
    });
  });

  it('displays invoice number column', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices, total: 4, page: 1, page_size: 20, total_pages: 1,
    });
    render(<InvoiceList />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('INV-2025-0001')).toBeInTheDocument();
    });
  });

  it('displays cost column with amounts', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices, total: 4, page: 1, page_size: 20, total_pages: 1,
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
      items: mockInvoices, total: 4, page: 1, page_size: 20, total_pages: 1,
    });
    render(<InvoiceList />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('invoice-status-sent')).toBeInTheDocument();
      expect(screen.getByTestId('invoice-status-overdue')).toBeInTheDocument();
      // Cluster E: now two paid invoices in the fixture.
      expect(screen.getAllByTestId('invoice-status-paid').length).toBeGreaterThan(0);
    });
  });

  it('displays job link column', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices, total: 4, page: 1, page_size: 20, total_pages: 1,
    });
    render(<InvoiceList />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('invoice-job-link-123e4567-e89b-12d3-a456-426614174000')).toBeInTheDocument();
    });
  });

  it('displays payment type for paid invoices', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices, total: 4, page: 1, page_size: 20, total_pages: 1,
    });
    render(<InvoiceList />, { wrapper: createWrapper() });
    // "Venmo" appears in both the Payment Type column (text label) and
    // the Channel pill column added by plan §Phase 3.7. Use getAllByText
    // so the test passes for both renderings.
    await waitFor(() => {
      expect(screen.getAllByText('Venmo').length).toBeGreaterThan(0);
    });
  });

  it('displays actions column', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices, total: 4, page: 1, page_size: 20, total_pages: 1,
    });
    render(<InvoiceList />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(
        screen.getByTestId('invoice-actions-123e4567-e89b-12d3-a456-426614174000'),
      ).toBeInTheDocument();
    });
  });

  it('renders filter panel', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices, total: 4, page: 1, page_size: 20, total_pages: 1,
    });
    render(<InvoiceList />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('filter-panel')).toBeInTheDocument();
      expect(screen.getByTestId('filter-toggle')).toBeInTheDocument();
    });
  });

  it('renders mass notify button', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices, total: 4, page: 1, page_size: 20, total_pages: 1,
    });
    render(<InvoiceList />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('mass-notify-btn')).toBeInTheDocument();
    });
  });

  it('renders pagination when multiple pages', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices, total: 50, page: 1, page_size: 20, total_pages: 3,
    });
    render(<InvoiceList />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('pagination-prev')).toBeInTheDocument();
      expect(screen.getByTestId('pagination-next')).toBeInTheDocument();
    });
  });

  it('has correct data-testid on list container', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices, total: 4, page: 1, page_size: 20, total_pages: 1,
    });
    render(<InvoiceList />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('invoice-list')).toBeInTheDocument();
    });
  });

  it('shows empty state when no invoices', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: [], total: 0, page: 1, page_size: 20, total_pages: 0,
    });
    render(<InvoiceList />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('No invoices found.')).toBeInTheDocument();
    });
  });

  it('shows loading state initially', () => {
    vi.mocked(invoiceApi.list).mockImplementation(() => new Promise(() => {}));
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

  it('renders paid_at cell as localized date for paid invoice', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices, total: 4, page: 1, page_size: 20, total_pages: 1,
    });
    render(<InvoiceList />, { wrapper: createWrapper() });
    await waitFor(() => {
      const cell = screen.getByTestId('paid-at-cell-423e4567-e89b-12d3-a456-426614174000');
      expect(cell).toBeInTheDocument();
      expect(cell.textContent).toMatch(/2025/);
    });
  });

  it('renders em-dash in paid_at cell for unpaid invoice', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices, total: 4, page: 1, page_size: 20, total_pages: 1,
    });
    render(<InvoiceList />, { wrapper: createWrapper() });
    await waitFor(() => {
      const cell = screen.getByTestId('paid-at-cell-123e4567-e89b-12d3-a456-426614174000');
      expect(cell.textContent).toBe('—');
    });
  });

  it('strips stripe: prefix from payment_reference display', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices, total: 4, page: 1, page_size: 20, total_pages: 1,
    });
    render(<InvoiceList />, { wrapper: createWrapper() });
    await waitFor(() => {
      const cell = screen.getByTestId('payment-reference-cell-423e4567-e89b-12d3-a456-426614174000');
      expect(cell.textContent).not.toContain('stripe:');
      expect(cell.textContent).toContain('pi_3OabcXYZ');
    });
  });

  it('displays raw payment_reference for non-Stripe invoices', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices, total: 4, page: 1, page_size: 20, total_pages: 1,
    });
    render(<InvoiceList />, { wrapper: createWrapper() });
    await waitFor(() => {
      const cell = screen.getByTestId('payment-reference-cell-323e4567-e89b-12d3-a456-426614174000');
      expect(cell.textContent).toContain('VNM123456');
    });
  });

  it('copies bare Stripe charge id to clipboard on click', async () => {
    const user = userEvent.setup();
    // userEvent.setup() v14 installs its own navigator.clipboard, so spy
    // AFTER setup to ensure we observe the call.
    const writeTextSpy = vi
      .spyOn(navigator.clipboard, 'writeText')
      .mockResolvedValue(undefined);
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: mockInvoices, total: 4, page: 1, page_size: 20, total_pages: 1,
    });
    render(<InvoiceList />, { wrapper: createWrapper() });
    const cell = await screen.findByTestId(
      'payment-reference-cell-423e4567-e89b-12d3-a456-426614174000',
    );
    await user.click(cell);
    expect(writeTextSpy).toHaveBeenCalledWith('pi_3OabcXYZ123456789');
  });
});
