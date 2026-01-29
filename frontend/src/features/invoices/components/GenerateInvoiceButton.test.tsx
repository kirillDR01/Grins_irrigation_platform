import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { GenerateInvoiceButton } from './GenerateInvoiceButton';
import { invoiceApi } from '../api/invoiceApi';
import type { Job } from '@/features/jobs/types';

// Mock the invoice API
vi.mock('../api/invoiceApi', () => ({
  invoiceApi: {
    generateFromJob: vi.fn(),
  },
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const createMockJob = (overrides: Partial<Job> = {}): Job => ({
  id: 'job-123',
  customer_id: 'customer-123',
  property_id: null,
  service_offering_id: null,
  job_type: 'spring_startup',
  category: 'ready_to_schedule',
  status: 'completed',
  description: 'Test job',
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
  requested_at: null,
  approved_at: null,
  scheduled_at: null,
  started_at: null,
  completed_at: '2026-01-29T00:00:00Z',
  closed_at: null,
  created_at: '2026-01-28T00:00:00Z',
  updated_at: '2026-01-29T00:00:00Z',
  ...overrides,
});

const renderWithRouter = (ui: React.ReactElement) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
};

describe('GenerateInvoiceButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders button for completed job without payment collected', () => {
    const job = createMockJob({ status: 'completed', payment_collected_on_site: false });
    renderWithRouter(<GenerateInvoiceButton job={job} />);
    
    expect(screen.getByTestId('generate-invoice-btn')).toBeInTheDocument();
    expect(screen.getByText('Generate Invoice')).toBeInTheDocument();
  });

  it('renders button for closed job without payment collected', () => {
    const job = createMockJob({ status: 'closed', payment_collected_on_site: false });
    renderWithRouter(<GenerateInvoiceButton job={job} />);
    
    expect(screen.getByTestId('generate-invoice-btn')).toBeInTheDocument();
  });

  it('does not render when payment_collected_on_site is true', () => {
    const job = createMockJob({ status: 'completed', payment_collected_on_site: true });
    renderWithRouter(<GenerateInvoiceButton job={job} />);
    
    expect(screen.queryByTestId('generate-invoice-btn')).not.toBeInTheDocument();
  });

  it('does not render for requested job', () => {
    const job = createMockJob({ status: 'requested', payment_collected_on_site: false });
    renderWithRouter(<GenerateInvoiceButton job={job} />);
    
    expect(screen.queryByTestId('generate-invoice-btn')).not.toBeInTheDocument();
  });

  it('does not render for approved job', () => {
    const job = createMockJob({ status: 'approved', payment_collected_on_site: false });
    renderWithRouter(<GenerateInvoiceButton job={job} />);
    
    expect(screen.queryByTestId('generate-invoice-btn')).not.toBeInTheDocument();
  });

  it('does not render for scheduled job', () => {
    const job = createMockJob({ status: 'scheduled', payment_collected_on_site: false });
    renderWithRouter(<GenerateInvoiceButton job={job} />);
    
    expect(screen.queryByTestId('generate-invoice-btn')).not.toBeInTheDocument();
  });

  it('does not render for in_progress job', () => {
    const job = createMockJob({ status: 'in_progress', payment_collected_on_site: false });
    renderWithRouter(<GenerateInvoiceButton job={job} />);
    
    expect(screen.queryByTestId('generate-invoice-btn')).not.toBeInTheDocument();
  });

  it('does not render for cancelled job', () => {
    const job = createMockJob({ status: 'cancelled', payment_collected_on_site: false });
    renderWithRouter(<GenerateInvoiceButton job={job} />);
    
    expect(screen.queryByTestId('generate-invoice-btn')).not.toBeInTheDocument();
  });

  it('calls generateFromJob API when clicked', async () => {
    const job = createMockJob({ status: 'completed', payment_collected_on_site: false });
    const mockInvoice = { id: 'invoice-123', invoice_number: 'INV-2026-001' };
    vi.mocked(invoiceApi.generateFromJob).mockResolvedValue(mockInvoice as never);
    
    renderWithRouter(<GenerateInvoiceButton job={job} />);
    
    fireEvent.click(screen.getByTestId('generate-invoice-btn'));
    
    await waitFor(() => {
      expect(invoiceApi.generateFromJob).toHaveBeenCalledWith('job-123');
    });
  });

  it('navigates to invoice detail on success', async () => {
    const job = createMockJob({ status: 'completed', payment_collected_on_site: false });
    const mockInvoice = { id: 'invoice-123', invoice_number: 'INV-2026-001' };
    vi.mocked(invoiceApi.generateFromJob).mockResolvedValue(mockInvoice as never);
    
    renderWithRouter(<GenerateInvoiceButton job={job} />);
    
    fireEvent.click(screen.getByTestId('generate-invoice-btn'));
    
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/invoices/invoice-123');
    });
  });

  it('calls onSuccess callback when provided', async () => {
    const job = createMockJob({ status: 'completed', payment_collected_on_site: false });
    const mockInvoice = { id: 'invoice-123', invoice_number: 'INV-2026-001' };
    vi.mocked(invoiceApi.generateFromJob).mockResolvedValue(mockInvoice as never);
    const onSuccess = vi.fn();
    
    renderWithRouter(<GenerateInvoiceButton job={job} onSuccess={onSuccess} />);
    
    fireEvent.click(screen.getByTestId('generate-invoice-btn'));
    
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith('invoice-123');
    });
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('shows loading state while generating', async () => {
    const job = createMockJob({ status: 'completed', payment_collected_on_site: false });
    vi.mocked(invoiceApi.generateFromJob).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ id: 'invoice-123', invoice_number: 'INV-2026-001' } as never), 100))
    );
    
    renderWithRouter(<GenerateInvoiceButton job={job} />);
    
    fireEvent.click(screen.getByTestId('generate-invoice-btn'));
    
    expect(screen.getByTestId('generate-invoice-btn')).toBeDisabled();
  });

  it('handles API error gracefully', async () => {
    const job = createMockJob({ status: 'completed', payment_collected_on_site: false });
    vi.mocked(invoiceApi.generateFromJob).mockRejectedValue(new Error('API Error'));
    
    renderWithRouter(<GenerateInvoiceButton job={job} />);
    
    fireEvent.click(screen.getByTestId('generate-invoice-btn'));
    
    await waitFor(() => {
      expect(invoiceApi.generateFromJob).toHaveBeenCalled();
    });
    
    // Button should be enabled again after error
    await waitFor(() => {
      expect(screen.getByTestId('generate-invoice-btn')).not.toBeDisabled();
    });
  });
});
