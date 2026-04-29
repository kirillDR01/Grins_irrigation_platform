/**
 * Tests for PaymentCollector — Architecture C (Stripe Payment Links).
 *
 * Validates: plan §Phase 3.1 branches:
 *  - "Send Payment Link" primary CTA when invoice exists
 *  - "Create Invoice & Send Payment Link" when no invoice yet
 *  - "Resend Payment Link" once a link has already been sent
 *  - lead-only message replaces the CTA
 *  - service-agreement guard hides the CTA entirely
 *  - copy-link UX appears when an active link exists
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PaymentCollector } from './PaymentCollector';
import { invoiceApi } from '@/features/invoices/api/invoiceApi';
import { appointmentApi } from '../api/appointmentApi';
import type { Invoice } from '@/features/invoices/types';

vi.mock('@/features/invoices/api/invoiceApi', () => ({
  invoiceApi: {
    list: vi.fn(),
    sendPaymentLink: vi.fn(),
  },
}));

vi.mock('../api/appointmentApi', () => ({
  appointmentApi: {
    createInvoice: vi.fn(),
    collectPayment: vi.fn(),
  },
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function buildInvoice(overrides: Partial<Invoice> = {}): Invoice {
  return {
    id: 'inv-1',
    job_id: 'job-1',
    customer_id: 'cust-1',
    invoice_number: 'INV-1',
    amount: 150,
    late_fee_amount: 0,
    total_amount: 150,
    invoice_date: '2026-04-28',
    due_date: '2026-05-13',
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
    customer_name: 'Test Customer',
    days_until_due: 15,
    days_past_due: null,
    stripe_payment_link_id: null,
    stripe_payment_link_url: null,
    stripe_payment_link_active: true,
    payment_link_sent_at: null,
    payment_link_sent_count: 0,
    created_at: '2026-04-28T00:00:00Z',
    updated_at: '2026-04-28T00:00:00Z',
    ...overrides,
  };
}

const baseProps = {
  appointmentId: 'appt-1',
  jobId: 'job-1',
  customerPhone: '+15555555555',
  customerEmail: 'c@example.com',
};

describe('PaymentCollector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when service agreement is active', () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: [], total: 0, page: 1, page_size: 50, total_pages: 0,
    });
    const { container } = render(
      <PaymentCollector {...baseProps} serviceAgreementActive={true} />,
      { wrapper: createWrapper() },
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders lead-only message when customerExists is false', () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: [], total: 0, page: 1, page_size: 50, total_pages: 0,
    });
    render(<PaymentCollector {...baseProps} customerExists={false} />, {
      wrapper: createWrapper(),
    });
    expect(screen.getByTestId('payment-collector-lead-only')).toBeInTheDocument();
    expect(screen.queryByTestId('send-payment-link-btn')).not.toBeInTheDocument();
  });

  it('shows "Create Invoice & Send Payment Link" when no invoice exists', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: [], total: 0, page: 1, page_size: 50, total_pages: 0,
    });
    render(<PaymentCollector {...baseProps} />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('send-payment-link-btn')).toHaveTextContent(
        'Create Invoice & Send Payment Link',
      );
    });
  });

  it('shows "Send Payment Link" when invoice exists but link not sent yet', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: [buildInvoice()], total: 1, page: 1, page_size: 50, total_pages: 1,
    });
    render(<PaymentCollector {...baseProps} />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('send-payment-link-btn')).toHaveTextContent(
        'Send Payment Link',
      );
    });
  });

  it('shows "Resend Payment Link" once link has been sent', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: [
        buildInvoice({
          payment_link_sent_count: 2,
          stripe_payment_link_url: 'https://buy.stripe.com/test_abc',
          stripe_payment_link_id: 'plink_abc',
        }),
      ],
      total: 1,
      page: 1,
      page_size: 50,
      total_pages: 1,
    });
    render(<PaymentCollector {...baseProps} />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('send-payment-link-btn')).toHaveTextContent(
        'Resend Payment Link',
      );
      expect(screen.getByTestId('payment-link-sent-indicator')).toBeInTheDocument();
    });
  });

  it('renders copy-link row when an active link exists', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: [
        buildInvoice({
          stripe_payment_link_url: 'https://buy.stripe.com/test_abc',
          stripe_payment_link_id: 'plink_abc',
          stripe_payment_link_active: true,
        }),
      ],
      total: 1,
      page: 1,
      page_size: 50,
      total_pages: 1,
    });
    render(<PaymentCollector {...baseProps} />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('payment-link-copy-row')).toBeInTheDocument();
      expect(screen.getByTestId('payment-link-url')).toHaveTextContent(
        'https://buy.stripe.com/test_abc',
      );
    });
  });

  it('calls sendPaymentLink mutation when primary button clicked with existing invoice', async () => {
    const user = userEvent.setup();
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: [buildInvoice()], total: 1, page: 1, page_size: 50, total_pages: 1,
    });
    vi.mocked(invoiceApi.sendPaymentLink).mockResolvedValue({
      channel: 'sms',
      link_url: 'https://buy.stripe.com/test_abc',
      sent_at: '2026-04-28T00:00:00Z',
      sent_count: 1,
    });
    render(<PaymentCollector {...baseProps} />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('send-payment-link-btn')).toBeInTheDocument();
    });
    await user.click(screen.getByTestId('send-payment-link-btn'));
    await waitFor(() => {
      expect(invoiceApi.sendPaymentLink).toHaveBeenCalledWith('inv-1');
    });
    expect(appointmentApi.createInvoice).not.toHaveBeenCalled();
  });

  it('creates the invoice first when none exists, then sends the link', async () => {
    const user = userEvent.setup();
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: [], total: 0, page: 1, page_size: 50, total_pages: 0,
    });
    vi.mocked(appointmentApi.createInvoice).mockResolvedValue({
      id: 'inv-new',
      invoice_number: 'INV-2',
      total_amount: 150,
      status: 'draft',
      payment_link: null,
    });
    vi.mocked(invoiceApi.sendPaymentLink).mockResolvedValue({
      channel: 'email',
      link_url: 'https://buy.stripe.com/test_xyz',
      sent_at: '2026-04-28T00:00:00Z',
      sent_count: 1,
    });
    render(<PaymentCollector {...baseProps} />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('send-payment-link-btn')).toHaveTextContent(
        'Create Invoice & Send Payment Link',
      );
    });
    await user.click(screen.getByTestId('send-payment-link-btn'));
    await waitFor(() => {
      expect(appointmentApi.createInvoice).toHaveBeenCalledWith('appt-1');
      expect(invoiceApi.sendPaymentLink).toHaveBeenCalledWith('inv-new');
    });
  });

  it('shows no-contact warning when customer has neither phone nor email', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: [buildInvoice()], total: 1, page: 1, page_size: 50, total_pages: 1,
    });
    render(
      <PaymentCollector
        appointmentId="appt-1"
        jobId="job-1"
        customerPhone={null}
        customerEmail={null}
      />,
      { wrapper: createWrapper() },
    );
    await waitFor(() => {
      expect(screen.getByTestId('payment-collector-no-contact')).toBeInTheDocument();
    });
  });
});
