import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { InvoiceForm } from './InvoiceForm';
import { invoiceApi } from '../api/invoiceApi';
import type { Invoice, InvoiceLineItem } from '../types';

// Mock the API
vi.mock('../api/invoiceApi', () => ({
  invoiceApi: {
    create: vi.fn(),
    update: vi.fn(),
  },
}));

const mockInvoice: Invoice = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  job_id: '123e4567-e89b-12d3-a456-426614174001',
  customer_id: '123e4567-e89b-12d3-a456-426614174002',
  invoice_number: 'INV-2025-0001',
  amount: 150.0,
  late_fee_amount: 0,
  total_amount: 150.0,
  invoice_date: '2025-01-15',
  due_date: '2025-01-30',
  status: 'draft',
  payment_method: null,
  payment_reference: null,
  paid_at: null,
  paid_amount: null,
  reminder_count: 0,
  last_reminder_sent: null,
  lien_eligible: false,
  lien_warning_sent: null,
  lien_filed_date: null,
  line_items: [
    { description: 'Spring Startup', quantity: 1, unit_price: 150.0, total: 150.0 },
  ],
  notes: 'Test notes',
  created_at: '2025-01-15T10:00:00Z',
  updated_at: '2025-01-15T10:00:00Z',
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('InvoiceForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders amount input', () => {
    render(<InvoiceForm jobId="test-job-id" />, { wrapper: createWrapper() });
    expect(screen.getByTestId('invoice-amount')).toBeInTheDocument();
  });

  it('renders due date picker', () => {
    render(<InvoiceForm jobId="test-job-id" />, { wrapper: createWrapper() });
    expect(screen.getByTestId('due-date-input')).toBeInTheDocument();
  });

  it('renders notes field', () => {
    render(<InvoiceForm jobId="test-job-id" />, { wrapper: createWrapper() });
    expect(screen.getByTestId('notes-input')).toBeInTheDocument();
  });

  it('renders add line item button', () => {
    render(<InvoiceForm jobId="test-job-id" />, { wrapper: createWrapper() });
    expect(screen.getByTestId('add-line-item-btn')).toBeInTheDocument();
  });

  it('add line item works', async () => {
    const user = userEvent.setup();
    render(<InvoiceForm jobId="test-job-id" />, { wrapper: createWrapper() });

    await user.click(screen.getByTestId('add-line-item-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('line-item-0')).toBeInTheDocument();
      expect(screen.getByTestId('line-item-description')).toBeInTheDocument();
    });
  });

  it('remove line item works', async () => {
    const user = userEvent.setup();
    render(<InvoiceForm jobId="test-job-id" />, { wrapper: createWrapper() });

    // Add a line item first
    await user.click(screen.getByTestId('add-line-item-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('line-item-0')).toBeInTheDocument();
    });

    // Remove it
    await user.click(screen.getByTestId('remove-line-item-btn'));

    await waitFor(() => {
      expect(screen.queryByTestId('line-item-0')).not.toBeInTheDocument();
    });
  });

  it('form validation shows error for missing amount', async () => {
    const user = userEvent.setup();
    render(<InvoiceForm jobId="test-job-id" />, { wrapper: createWrapper() });

    // Clear the amount field
    const amountInput = screen.getByTestId('invoice-amount');
    await user.clear(amountInput);
    await user.type(amountInput, '0');

    await user.click(screen.getByTestId('submit-invoice-btn'));

    await waitFor(() => {
      expect(screen.getByText('Amount must be positive')).toBeInTheDocument();
    });
  });

  it('submit creates invoice', async () => {
    const user = userEvent.setup();
    const onSuccess = vi.fn();
    vi.mocked(invoiceApi.create).mockResolvedValue(mockInvoice);

    render(
      <InvoiceForm jobId="test-job-id" defaultAmount={150} onSuccess={onSuccess} />,
      { wrapper: createWrapper() },
    );

    await user.click(screen.getByTestId('submit-invoice-btn'));

    await waitFor(() => {
      expect(invoiceApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          job_id: 'test-job-id',
          amount: 150,
        }),
      );
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it('has correct data-testid on form', () => {
    render(<InvoiceForm jobId="test-job-id" />, { wrapper: createWrapper() });
    expect(screen.getByTestId('invoice-form')).toBeInTheDocument();
  });

  it('renders with existing invoice data for editing', () => {
    render(<InvoiceForm invoice={mockInvoice} />, { wrapper: createWrapper() });

    const amountInput = screen.getByTestId('invoice-amount') as HTMLInputElement;
    expect(amountInput.value).toBe('150');

    const notesInput = screen.getByTestId('notes-input') as HTMLTextAreaElement;
    expect(notesInput.value).toBe('Test notes');
  });

  it('shows Update Invoice button when editing', () => {
    render(<InvoiceForm invoice={mockInvoice} />, { wrapper: createWrapper() });
    expect(screen.getByText('Update Invoice')).toBeInTheDocument();
  });

  it('shows Create Invoice button when creating', () => {
    render(<InvoiceForm jobId="test-job-id" />, { wrapper: createWrapper() });
    expect(screen.getByText('Create Invoice')).toBeInTheDocument();
  });

  it('cancel button calls onCancel', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();

    render(<InvoiceForm jobId="test-job-id" onCancel={onCancel} />, {
      wrapper: createWrapper(),
    });

    await user.click(screen.getByTestId('cancel-btn'));

    expect(onCancel).toHaveBeenCalled();
  });

  it('renders late fee input', () => {
    render(<InvoiceForm jobId="test-job-id" />, { wrapper: createWrapper() });
    expect(screen.getByTestId('late-fee-input')).toBeInTheDocument();
  });

  it('renders with default line items', () => {
    const defaultLineItems: InvoiceLineItem[] = [
      { description: 'Test Service', quantity: 2, unit_price: 75.0, total: 150.0 },
    ];

    render(
      <InvoiceForm jobId="test-job-id" defaultLineItems={defaultLineItems} />,
      { wrapper: createWrapper() },
    );

    expect(screen.getByTestId('line-item-0')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Test Service')).toBeInTheDocument();
  });
});
