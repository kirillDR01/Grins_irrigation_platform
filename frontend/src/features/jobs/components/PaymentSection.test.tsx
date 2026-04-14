/**
 * Unit tests for PaymentSection conditional rendering.
 * Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.6
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { PaymentSection } from './PaymentSection';
import type { Job } from '../types';
import type { Invoice } from '@/features/invoices';

// Mock the invoices feature hooks
const mockUseInvoicesByJob = vi.fn();
vi.mock('@/features/invoices', async () => {
  const actual = await vi.importActual<typeof import('@/features/invoices')>('@/features/invoices');
  return {
    ...actual,
    useInvoicesByJob: (...args: unknown[]) => mockUseInvoicesByJob(...args),
    GenerateInvoiceButton: ({ job }: { job: Job }) => (
      <button data-testid="generate-invoice-btn">Generate Invoice for {job.id}</button>
    ),
    InvoiceStatusBadge: ({ status }: { status: string }) => (
      <span data-testid={`invoice-status-${status}`}>{status}</span>
    ),
  };
});

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

const baseJob: Job = {
  id: 'job-001',
  customer_id: 'cust-001',
  property_id: null,
  service_offering_id: null,
  service_agreement_id: null,
  job_type: 'spring_startup',
  category: 'ready_to_schedule',
  status: 'completed',
  description: null,
  summary: null,
  notes: null,
  estimated_duration_minutes: 60,
  priority_level: 0,
  weather_sensitive: false,
  staffing_required: 1,
  equipment_required: null,
  materials_required: null,
  quoted_amount: 150,
  final_amount: 150,
  source: null,
  source_details: null,
  payment_collected_on_site: false,
  target_start_date: null,
  target_end_date: null,
  requested_at: null,
  approved_at: null,
  scheduled_at: null,
  started_at: null,
  completed_at: '2025-06-01T12:00:00Z',
  closed_at: null,
  created_at: '2025-05-01T10:00:00Z',
  updated_at: '2025-06-01T12:00:00Z',
  customer_name: 'John Doe',
  customer_phone: '555-1234',
  customer_tags: null,
  property_address: '123 Main St',
  property_city: 'Springfield',
  property_type: 'residential',
  property_is_hoa: false,
  property_is_subscription: false,
  on_my_way_at: null,
  time_tracking_metadata: null,
  service_preference_notes: null,
  service_agreement_name: null,
  service_agreement_active: null,
  customer_address: '123 Main St',
  property_tags: null,
};

const mockInvoice: Invoice = {
  id: 'inv-001',
  job_id: 'job-001',
  customer_id: 'cust-001',
  invoice_number: 'INV-1001',
  amount: 150,
  late_fee_amount: 0,
  total_amount: 150,
  invoice_date: '2025-06-01',
  due_date: '2025-07-01',
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
  created_at: '2025-06-01T10:00:00Z',
  updated_at: '2025-06-01T10:00:00Z',
};

describe('PaymentSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseInvoicesByJob.mockReturnValue({ data: undefined });
  });

  /**
   * Req 17.1: Service agreement job → "Covered" display, no payment buttons
   */
  it('shows "Covered by Agreement" for job with active service agreement', () => {
    const agreementJob: Job = {
      ...baseJob,
      service_agreement_id: 'agr-001',
      service_agreement_active: true,
      service_agreement_name: 'Professional Plan',
    };

    render(<PaymentSection job={agreementJob} />, { wrapper: createWrapper() });

    const section = screen.getByTestId('payment-section-agreement');
    expect(section).toBeInTheDocument();
    expect(screen.getByText(/Covered by Professional Plan/)).toBeInTheDocument();
    expect(screen.getByText(/no payment needed/)).toBeInTheDocument();

    // No payment buttons should be present
    expect(screen.queryByTestId('collect-payment-btn')).not.toBeInTheDocument();
    expect(screen.queryByTestId('generate-invoice-btn')).not.toBeInTheDocument();
  });

  /**
   * Req 17.1: Falls back to "Service Agreement" when name is null
   */
  it('shows fallback name when service_agreement_name is null', () => {
    const agreementJob: Job = {
      ...baseJob,
      service_agreement_id: 'agr-001',
      service_agreement_active: true,
      service_agreement_name: null,
    };

    render(<PaymentSection job={agreementJob} />, { wrapper: createWrapper() });

    expect(screen.getByText(/Covered by Service Agreement/)).toBeInTheDocument();
  });

  /**
   * Req 17.2: One-off job with no invoice → both buttons shown
   */
  it('shows both Create Invoice and Collect Payment for one-off job with no invoice', () => {
    render(<PaymentSection job={baseJob} />, { wrapper: createWrapper() });

    const section = screen.getByTestId('payment-section-no-payment');
    expect(section).toBeInTheDocument();
    expect(screen.getByTestId('generate-invoice-btn')).toBeInTheDocument();
    expect(screen.getByTestId('collect-payment-btn')).toBeInTheDocument();
  });

  /**
   * Req 17.3: Invoice sent → invoice details shown with status badge
   */
  it('shows invoice details with badge when invoice is sent', () => {
    mockUseInvoicesByJob.mockReturnValue({ data: [mockInvoice] });

    render(<PaymentSection job={baseJob} />, { wrapper: createWrapper() });

    const section = screen.getByTestId('payment-section-invoice');
    expect(section).toBeInTheDocument();
    expect(screen.getByText(/Invoice #INV-1001/)).toBeInTheDocument();
    expect(screen.getByText(/\$150\.00/)).toBeInTheDocument();
    expect(screen.getByTestId('invoice-status-sent')).toBeInTheDocument();

    // Collect Payment should still be available
    expect(screen.getByTestId('collect-payment-btn')).toBeInTheDocument();
  });

  /**
   * Req 17.4: Paid on-site → payment confirmation shown with green checkmark
   */
  it('shows payment confirmation for job with on-site payment', () => {
    const paidJob: Job = {
      ...baseJob,
      payment_collected_on_site: true,
      final_amount: 175,
    };

    render(<PaymentSection job={paidJob} />, { wrapper: createWrapper() });

    const section = screen.getByTestId('payment-section-paid');
    expect(section).toBeInTheDocument();
    expect(screen.getByText(/Payment collected/)).toBeInTheDocument();
    expect(screen.getByText(/\$175\.00/)).toBeInTheDocument();

    // No payment buttons should be present
    expect(screen.queryByTestId('collect-payment-btn')).not.toBeInTheDocument();
    expect(screen.queryByTestId('generate-invoice-btn')).not.toBeInTheDocument();
  });

  /**
   * Req 17.4: Paid on-site with invoice payment method → shows method from invoice
   */
  it('shows payment method from invoice when available', () => {
    const paidJob: Job = {
      ...baseJob,
      payment_collected_on_site: true,
      final_amount: 200,
    };
    const paidInvoice: Invoice = {
      ...mockInvoice,
      status: 'paid',
      payment_method: 'cash',
      paid_amount: 200,
    };
    mockUseInvoicesByJob.mockReturnValue({ data: [paidInvoice] });

    render(<PaymentSection job={paidJob} />, { wrapper: createWrapper() });

    expect(screen.getByText(/via Cash/)).toBeInTheDocument();
  });

  /**
   * Req 17.6: Payment section renders conditionally based on payment path
   * Priority order: agreement → paid on-site → invoice → no payment
   */
  it('prioritizes agreement over paid-on-site when both are true', () => {
    const bothJob: Job = {
      ...baseJob,
      service_agreement_id: 'agr-001',
      service_agreement_active: true,
      service_agreement_name: 'Premium',
      payment_collected_on_site: true,
    };

    render(<PaymentSection job={bothJob} />, { wrapper: createWrapper() });

    // Agreement takes priority
    expect(screen.getByTestId('payment-section-agreement')).toBeInTheDocument();
    expect(screen.queryByTestId('payment-section-paid')).not.toBeInTheDocument();
  });

  it('prioritizes paid-on-site over invoice when both exist', () => {
    const paidWithInvoice: Job = {
      ...baseJob,
      payment_collected_on_site: true,
    };
    mockUseInvoicesByJob.mockReturnValue({ data: [mockInvoice] });

    render(<PaymentSection job={paidWithInvoice} />, { wrapper: createWrapper() });

    expect(screen.getByTestId('payment-section-paid')).toBeInTheDocument();
    expect(screen.queryByTestId('payment-section-invoice')).not.toBeInTheDocument();
  });

  it('shows no-payment section when agreement is inactive', () => {
    const inactiveAgreementJob: Job = {
      ...baseJob,
      service_agreement_id: 'agr-001',
      service_agreement_active: false,
      service_agreement_name: 'Expired Plan',
    };

    render(<PaymentSection job={inactiveAgreementJob} />, { wrapper: createWrapper() });

    // Inactive agreement should NOT trigger the agreement display
    expect(screen.queryByTestId('payment-section-agreement')).not.toBeInTheDocument();
    expect(screen.getByTestId('payment-section-no-payment')).toBeInTheDocument();
  });
});
