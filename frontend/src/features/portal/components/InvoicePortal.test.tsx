import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { InvoicePortal } from './InvoicePortal';
import type { PortalInvoice } from '../types';

const mockInvoiceData: PortalInvoice = {
  business: {
    company_name: 'Grins Irrigation',
    company_logo_url: 'https://example.com/logo.png',
    company_address: '123 Main St, Austin TX',
    company_phone: '(555) 123-4567',
  },
  invoice_number: 'INV-2025-001',
  invoice_date: '2025-06-01',
  due_date: '2025-07-01',
  customer_name: 'Jane Doe',
  line_items: [
    { description: 'Sprinkler repair', quantity: 1, unit_price: 150.0, total: 150.0 },
    { description: 'Parts - valve', quantity: 2, unit_price: 25.0, total: 50.0 },
  ],
  total_amount: 200.0,
  amount_paid: 0,
  balance_due: 200.0,
  payment_status: 'SENT',
  stripe_payment_url: 'https://checkout.stripe.com/pay/test123',
};

const mockUsePortalInvoice = vi.fn();

vi.mock('../hooks', () => ({
  usePortalInvoice: (...args: unknown[]) => mockUsePortalInvoice(...args),
}));

function renderWithProviders(token = 'invoice-token-123') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/portal/invoices/${token}`]}>
        <Routes>
          <Route path="/portal/invoices/:token" element={<InvoicePortal />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('InvoicePortal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state', () => {
    mockUsePortalInvoice.mockReturnValue({ data: undefined, isLoading: true, error: null });
    renderWithProviders();
    expect(screen.getByTestId('invoice-loading')).toBeInTheDocument();
  });

  it('renders expired state for 410 error with contact info', () => {
    mockUsePortalInvoice.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: { response: { status: 410 } },
    });
    renderWithProviders();
    expect(screen.getByTestId('invoice-expired')).toBeInTheDocument();
    expect(screen.getByText(/90 days/)).toBeInTheDocument();
    expect(screen.getByTestId('expired-contact-info')).toBeInTheDocument();
  });

  it('renders error state for other errors', () => {
    mockUsePortalInvoice.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: { response: { status: 500 } },
    });
    renderWithProviders();
    expect(screen.getByTestId('invoice-error')).toBeInTheDocument();
  });

  it('renders invoice details with company branding', () => {
    mockUsePortalInvoice.mockReturnValue({ data: mockInvoiceData, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('invoice-portal-page')).toBeInTheDocument();
    expect(screen.getByTestId('company-logo')).toBeInTheDocument();
    expect(screen.getByText('Grins Irrigation')).toBeInTheDocument();
    expect(screen.getByText('123 Main St, Austin TX')).toBeInTheDocument();
    expect(screen.getByText('(555) 123-4567')).toBeInTheDocument();
    expect(screen.getByText((_content, element) => element?.tagName === 'H2' && element?.textContent?.includes('INV-2025-001') === true)).toBeInTheDocument();
    expect(screen.getByText('Jane Doe')).toBeInTheDocument();
  });

  it('renders line items table', () => {
    mockUsePortalInvoice.mockReturnValue({ data: mockInvoiceData, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('invoice-line-items-table')).toBeInTheDocument();
    expect(screen.getByText('Sprinkler repair')).toBeInTheDocument();
    expect(screen.getByText('Parts - valve')).toBeInTheDocument();
  });

  it('renders totals section with balance due', () => {
    mockUsePortalInvoice.mockReturnValue({ data: mockInvoiceData, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('invoice-totals')).toBeInTheDocument();
    expect(screen.getByText('Balance Due')).toBeInTheDocument();
  });

  it('renders Pay Now button with Stripe link when balance > 0', () => {
    mockUsePortalInvoice.mockReturnValue({ data: mockInvoiceData, isLoading: false, error: null });
    renderWithProviders();

    const payBtn = screen.getByTestId('pay-now-btn');
    expect(payBtn).toBeInTheDocument();
    const link = payBtn.closest('a');
    expect(link).toHaveAttribute('href', 'https://checkout.stripe.com/pay/test123');
    expect(link).toHaveAttribute('target', '_blank');
  });

  it('renders Paid in Full when balance is 0', () => {
    const paidInvoice: PortalInvoice = {
      ...mockInvoiceData,
      amount_paid: 200.0,
      balance_due: 0,
      payment_status: 'PAID',
    };
    mockUsePortalInvoice.mockReturnValue({ data: paidInvoice, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('paid-confirmation')).toBeInTheDocument();
    expect(screen.getByText('Paid in Full')).toBeInTheDocument();
    expect(screen.queryByTestId('pay-now-btn')).not.toBeInTheDocument();
  });

  it('renders payment unavailable when no Stripe URL and balance > 0', () => {
    const noStripeInvoice: PortalInvoice = {
      ...mockInvoiceData,
      stripe_payment_url: null,
    };
    mockUsePortalInvoice.mockReturnValue({ data: noStripeInvoice, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('payment-unavailable')).toBeInTheDocument();
  });

  it('renders status badge', () => {
    mockUsePortalInvoice.mockReturnValue({ data: mockInvoiceData, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('invoice-status-badge')).toBeInTheDocument();
    expect(screen.getByText('Sent')).toBeInTheDocument();
  });

  it('does not expose internal IDs in the rendered output', () => {
    mockUsePortalInvoice.mockReturnValue({ data: mockInvoiceData, isLoading: false, error: null });
    const { container } = renderWithProviders();
    const html = container.innerHTML;

    expect(html).not.toMatch(/customer_id|lead_id|staff_id|job_id/);
  });

  it('shows amount paid when partially paid', () => {
    const partialInvoice: PortalInvoice = {
      ...mockInvoiceData,
      amount_paid: 100.0,
      balance_due: 100.0,
      payment_status: 'PARTIAL',
    };
    mockUsePortalInvoice.mockReturnValue({ data: partialInvoice, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByText('Amount Paid')).toBeInTheDocument();
  });
});
