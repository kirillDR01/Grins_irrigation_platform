import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { InvoiceDetail } from './InvoiceDetail';
import { invoiceApi } from '../api/invoiceApi';
import type { InvoiceDetail as InvoiceDetailType } from '../types';

// Mock the API
vi.mock('../api/invoiceApi', () => ({
  invoiceApi: {
    get: vi.fn(),
    send: vi.fn(),
    recordPayment: vi.fn(),
    sendReminder: vi.fn(),
    sendLienWarning: vi.fn(),
    markLienFiled: vi.fn(),
  },
}));

// Mock react-router-dom hooks
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ id: 'test-invoice-id' }),
    useNavigate: () => vi.fn(),
  };
});

const mockInvoice: InvoiceDetailType = {
  id: 'test-invoice-id',
  job_id: 'test-job-id',
  customer_id: 'test-customer-id',
  invoice_number: 'INV-2025-0001',
  amount: 150.0,
  late_fee_amount: 0,
  total_amount: 150.0,
  invoice_date: '2025-01-15',
  due_date: '2025-02-15',
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
    { description: 'Spring Startup', quantity: 1, unit_price: 100.0, total: 100.0 },
    { description: 'Additional Zone', quantity: 2, unit_price: 25.0, total: 50.0 },
  ],
  notes: 'Test invoice notes',
  job_description: 'Spring startup service',
  customer_name: 'John Doe',
  customer_phone: '612-555-1234',
  customer_email: 'john@example.com',
  created_at: '2025-01-15T10:00:00Z',
  updated_at: '2025-01-15T10:00:00Z',
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}

describe('InvoiceDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(invoiceApi.get).mockResolvedValue(mockInvoice);
  });

  it('renders invoice detail with all fields', async () => {
    render(<InvoiceDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('invoice-detail')).toBeInTheDocument();
    });

    expect(screen.getByTestId('invoice-number')).toHaveTextContent('INV-2025-0001');
    expect(screen.getByTestId('invoice-amount')).toHaveTextContent('$150.00');
  });

  it('displays job info', async () => {
    render(<InvoiceDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Spring startup service')).toBeInTheDocument();
    });
  });

  it('displays customer info', async () => {
    render(<InvoiceDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('612-555-1234')).toBeInTheDocument();
      expect(screen.getByText('john@example.com')).toBeInTheDocument();
    });
  });

  it('displays line items', async () => {
    render(<InvoiceDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('invoice-line-items')).toBeInTheDocument();
    });

    expect(screen.getByText('Spring Startup')).toBeInTheDocument();
    expect(screen.getByText('Additional Zone')).toBeInTheDocument();
  });

  it('shows action buttons based on status', async () => {
    render(<InvoiceDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('send-invoice-btn')).toBeInTheDocument();
    });
  });

  it('shows send invoice button for draft status', async () => {
    render(<InvoiceDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('send-invoice-btn')).toBeInTheDocument();
    });
  });

  it('shows record payment button for sent status', async () => {
    vi.mocked(invoiceApi.get).mockResolvedValue({
      ...mockInvoice,
      status: 'sent',
    });

    const onRecordPayment = vi.fn();
    render(<InvoiceDetail onRecordPayment={onRecordPayment} />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('record-payment-btn')).toBeInTheDocument();
    });
  });

  it('shows send reminder button for overdue status', async () => {
    vi.mocked(invoiceApi.get).mockResolvedValue({
      ...mockInvoice,
      status: 'overdue',
    });

    render(<InvoiceDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('send-reminder-btn')).toBeInTheDocument();
    });
  });

  it('shows lien warning button for eligible overdue invoices', async () => {
    vi.mocked(invoiceApi.get).mockResolvedValue({
      ...mockInvoice,
      status: 'overdue',
      lien_eligible: true,
      lien_warning_sent: null,
    });

    render(<InvoiceDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('send-lien-warning-btn')).toBeInTheDocument();
    });
  });

  it('shows mark lien filed button after warning sent', async () => {
    vi.mocked(invoiceApi.get).mockResolvedValue({
      ...mockInvoice,
      status: 'lien_warning',
      lien_eligible: true,
      lien_warning_sent: '2025-01-20T10:00:00Z',
      lien_filed_date: null,
    });

    render(<InvoiceDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('mark-lien-filed-btn')).toBeInTheDocument();
    });
  });

  it('displays payment information when paid', async () => {
    vi.mocked(invoiceApi.get).mockResolvedValue({
      ...mockInvoice,
      status: 'paid',
      paid_at: '2025-01-20T10:00:00Z',
      paid_amount: 150.0,
      payment_method: 'venmo',
      payment_reference: 'VEN-12345',
    });

    render(<InvoiceDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('venmo')).toBeInTheDocument();
      expect(screen.getByText('VEN-12345')).toBeInTheDocument();
    });
  });

  it('displays lien information for eligible invoices', async () => {
    vi.mocked(invoiceApi.get).mockResolvedValue({
      ...mockInvoice,
      lien_eligible: true,
    });

    render(<InvoiceDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/eligible for mechanic's lien/i)).toBeInTheDocument();
    });
  });

  it('displays reminder count when reminders sent', async () => {
    vi.mocked(invoiceApi.get).mockResolvedValue({
      ...mockInvoice,
      reminder_count: 2,
      last_reminder_sent: '2025-01-25T10:00:00Z',
    });

    render(<InvoiceDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      // Check for the Reminders section
      expect(screen.getByText('Reminders')).toBeInTheDocument();
    });
    
    // Check that the reminder count is displayed in the Reminders section
    expect(screen.getByText('Reminders Sent')).toBeInTheDocument();
  });

  it('calls send invoice API when button clicked', async () => {
    const user = userEvent.setup();
    vi.mocked(invoiceApi.send).mockResolvedValue({ ...mockInvoice, status: 'sent' });

    render(<InvoiceDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('send-invoice-btn')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('send-invoice-btn'));

    await waitFor(() => {
      expect(invoiceApi.send).toHaveBeenCalledWith('test-invoice-id');
    });
  });

  it('displays remaining balance when partially paid', async () => {
    vi.mocked(invoiceApi.get).mockResolvedValue({
      ...mockInvoice,
      status: 'partial',
      paid_amount: 50.0,
    });

    render(<InvoiceDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/Remaining Balance/i)).toBeInTheDocument();
    });
    
    // Check that the remaining balance section exists with the correct value
    const remainingBalanceSection = screen.getByText(/Remaining Balance/i).closest('div');
    expect(remainingBalanceSection).toHaveTextContent('$100.00');
  });

  it('displays notes when present', async () => {
    render(<InvoiceDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Test invoice notes')).toBeInTheDocument();
    });
  });
});
