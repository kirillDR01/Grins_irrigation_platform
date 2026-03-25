/**
 * Tests for InvoiceMetricsWidget component.
 * Validates: Requirements 5.1, 5.3
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { InvoiceMetricsWidget } from './InvoiceMetricsWidget';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('../hooks', () => ({
  usePendingInvoiceMetrics: vi.fn(),
}));

import { usePendingInvoiceMetrics } from '../hooks';
const mockUsePendingInvoiceMetrics = usePendingInvoiceMetrics as ReturnType<typeof vi.fn>;

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

describe('InvoiceMetricsWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders pending invoice count and total amount', () => {
    mockUsePendingInvoiceMetrics.mockReturnValue({
      data: { count: 7, total_amount: '3450.00' },
      isLoading: false,
    });

    render(<InvoiceMetricsWidget />, { wrapper: createWrapper() });

    const widget = screen.getByTestId('invoice-metrics-widget');
    expect(widget).toBeInTheDocument();
    expect(widget).toHaveTextContent('7');
    expect(widget).toHaveTextContent('$3,450.00 total');
    expect(widget).toHaveTextContent('Pending Invoices');
  });

  it('renders zero count with appropriate message', () => {
    mockUsePendingInvoiceMetrics.mockReturnValue({
      data: { count: 0, total_amount: '0' },
      isLoading: false,
    });

    render(<InvoiceMetricsWidget />, { wrapper: createWrapper() });

    const widget = screen.getByTestId('invoice-metrics-widget');
    expect(widget).toHaveTextContent('0');
    expect(widget).toHaveTextContent('No pending invoices');
  });

  it('shows dash while loading', () => {
    mockUsePendingInvoiceMetrics.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    render(<InvoiceMetricsWidget />, { wrapper: createWrapper() });

    const widget = screen.getByTestId('invoice-metrics-widget');
    expect(widget).toHaveTextContent('—');
  });

  it('applies emerald border when count > 0', () => {
    mockUsePendingInvoiceMetrics.mockReturnValue({
      data: { count: 3, total_amount: '1200.50' },
      isLoading: false,
    });

    render(<InvoiceMetricsWidget />, { wrapper: createWrapper() });

    const widget = screen.getByTestId('invoice-metrics-widget');
    expect(widget.className).toContain('border-emerald-200');
  });

  it('does not apply emerald border when count is 0', () => {
    mockUsePendingInvoiceMetrics.mockReturnValue({
      data: { count: 0, total_amount: '0' },
      isLoading: false,
    });

    render(<InvoiceMetricsWidget />, { wrapper: createWrapper() });

    const widget = screen.getByTestId('invoice-metrics-widget');
    expect(widget.className).not.toContain('border-emerald-200');
  });

  it('navigates to /invoices on click', () => {
    mockUsePendingInvoiceMetrics.mockReturnValue({
      data: { count: 5, total_amount: '2000.00' },
      isLoading: false,
    });

    render(<InvoiceMetricsWidget />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTestId('invoice-metrics-widget'));
    expect(mockNavigate).toHaveBeenCalledWith('/invoices');
  });

  it('navigates to /invoices on Enter key', () => {
    mockUsePendingInvoiceMetrics.mockReturnValue({
      data: { count: 2, total_amount: '800.00' },
      isLoading: false,
    });

    render(<InvoiceMetricsWidget />, { wrapper: createWrapper() });

    fireEvent.keyDown(screen.getByTestId('invoice-metrics-widget'), { key: 'Enter' });
    expect(mockNavigate).toHaveBeenCalledWith('/invoices');
  });

  it('navigates to /invoices on Space key', () => {
    mockUsePendingInvoiceMetrics.mockReturnValue({
      data: { count: 2, total_amount: '800.00' },
      isLoading: false,
    });

    render(<InvoiceMetricsWidget />, { wrapper: createWrapper() });

    fireEvent.keyDown(screen.getByTestId('invoice-metrics-widget'), { key: ' ' });
    expect(mockNavigate).toHaveBeenCalledWith('/invoices');
  });

  it('formats large currency amounts correctly', () => {
    mockUsePendingInvoiceMetrics.mockReturnValue({
      data: { count: 15, total_amount: '125750.99' },
      isLoading: false,
    });

    render(<InvoiceMetricsWidget />, { wrapper: createWrapper() });

    const widget = screen.getByTestId('invoice-metrics-widget');
    expect(widget).toHaveTextContent('$125,750.99 total');
  });
});
