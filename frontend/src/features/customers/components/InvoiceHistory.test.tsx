/**
 * H-9: InvoiceHistory re-fetches when invoice mutations elsewhere fire
 * `queryClient.invalidateQueries({ queryKey: customerInvoiceKeys.all })`.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import type { ReactNode } from 'react';
import { InvoiceHistory } from './InvoiceHistory';
import { customerApi } from '../api/customerApi';
import { customerInvoiceKeys } from '../hooks/useCustomers';

vi.mock('../api/customerApi', () => ({
  customerApi: {
    listInvoices: vi.fn(),
  },
}));

const baseInvoice = {
  id: 'inv-1',
  invoice_number: 'INV-2025-0001',
  date: '2025-04-01',
  due_date: '2025-05-01',
  total_amount: 150,
  status: 'sent' as const,
  days_until_due: 10,
  days_past_due: null,
  created_at: '2025-04-01T00:00:00Z',
  updated_at: '2025-04-01T00:00:00Z',
};

function createHarness() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
  return { queryClient, Wrapper };
}

describe('InvoiceHistory (H-9 real-time updates)', () => {
  beforeEach(() => {
    vi.mocked(customerApi.listInvoices).mockReset();
  });

  it('refetches after an external mutation invalidates customerInvoiceKeys', async () => {
    // 1st fetch: invoice is "sent".
    // 2nd fetch (after invalidation): invoice is "paid".
    vi.mocked(customerApi.listInvoices)
      .mockResolvedValueOnce({
        items: [baseInvoice],
        total: 1,
        page: 1,
        page_size: 10,
        total_pages: 1,
      })
      .mockResolvedValueOnce({
        items: [{ ...baseInvoice, status: 'paid' }],
        total: 1,
        page: 1,
        page_size: 10,
        total_pages: 1,
      });

    const { queryClient, Wrapper } = createHarness();

    render(<InvoiceHistory customerId="cust-1" />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('invoice-status-sent')).toBeInTheDocument();
    });
    expect(customerApi.listInvoices).toHaveBeenCalledTimes(1);

    // Simulate an invoice mutation elsewhere (e.g. useRecordPayment) firing
    // cross-query invalidation. The InvoiceHistory query must refetch.
    await queryClient.invalidateQueries({ queryKey: customerInvoiceKeys.all });

    await waitFor(() => {
      expect(screen.getByTestId('invoice-status-paid')).toBeInTheDocument();
    });
    expect(customerApi.listInvoices).toHaveBeenCalledTimes(2);
  });

  it('renders empty state when the customer has no invoices', async () => {
    vi.mocked(customerApi.listInvoices).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
      total_pages: 0,
    });

    const { Wrapper } = createHarness();
    render(<InvoiceHistory customerId="cust-1" />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('invoices-empty')).toBeInTheDocument();
    });
  });

  it('renders the invoice table with one row per invoice', async () => {
    vi.mocked(customerApi.listInvoices).mockResolvedValue({
      items: [baseInvoice],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });

    const { Wrapper } = createHarness();
    render(<InvoiceHistory customerId="cust-1" />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('invoice-history')).toBeInTheDocument();
    });
    expect(screen.getByTestId('invoice-row-inv-1')).toBeInTheDocument();
    expect(screen.getByText('INV-2025-0001')).toBeInTheDocument();
  });
});
