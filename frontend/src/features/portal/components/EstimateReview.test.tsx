import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { EstimateReview } from './EstimateReview';
import type { PortalEstimate } from '../types';

// Mock the hooks
const mockEstimateData: PortalEstimate = {
  company_name: 'Grins Irrigation',
  company_logo_url: 'https://example.com/logo.png',
  company_address: '123 Main St',
  company_phone: '(555) 123-4567',
  customer_name: 'John Smith',
  estimate_number: 'EST-001',
  status: 'SENT',
  line_items: [
    { item: 'Sprinkler Head', description: 'Replace broken sprinkler', unit_price: 45.0, quantity: 3 },
    { item: 'Labor', description: 'Installation labor', unit_price: 75.0, quantity: 2 },
  ],
  tiers: null,
  subtotal: 285.0,
  tax_amount: 22.8,
  discount_amount: 0,
  total: 307.8,
  promotion_code: null,
  notes: 'Work to be completed within 2 weeks.',
  valid_until: '2025-12-31',
  created_at: '2025-06-01T10:00:00Z',
  is_readonly: false,
};

const mockUsePortalEstimate = vi.fn();
const mockApproveEstimate = vi.fn();
const mockRejectEstimate = vi.fn();

vi.mock('../hooks', () => ({
  usePortalEstimate: (...args: unknown[]) => mockUsePortalEstimate(...args),
  useApproveEstimate: () => ({
    mutateAsync: mockApproveEstimate,
    isPending: false,
  }),
  useRejectEstimate: () => ({
    mutateAsync: mockRejectEstimate,
    isPending: false,
  }),
}));

function renderWithProviders(token = 'test-token-123') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/portal/estimates/${token}`]}>
        <Routes>
          <Route path="/portal/estimates/:token" element={<EstimateReview />} />
          <Route path="/portal/estimates/:token/confirmed" element={<div data-testid="confirmed-page">Confirmed</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('EstimateReview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state', () => {
    mockUsePortalEstimate.mockReturnValue({ data: undefined, isLoading: true, error: null });
    renderWithProviders();
    expect(screen.getByTestId('estimate-loading')).toBeInTheDocument();
  });

  it('renders expired state for 410 error', () => {
    mockUsePortalEstimate.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: { response: { status: 410 } },
    });
    renderWithProviders();
    expect(screen.getByTestId('estimate-expired')).toBeInTheDocument();
    expect(screen.getByText('Link Expired')).toBeInTheDocument();
  });

  it('renders error state for other errors', () => {
    mockUsePortalEstimate.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: { response: { status: 500 } },
    });
    renderWithProviders();
    expect(screen.getByTestId('estimate-error')).toBeInTheDocument();
  });

  it('renders estimate details with company branding', () => {
    mockUsePortalEstimate.mockReturnValue({ data: mockEstimateData, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('estimate-review-page')).toBeInTheDocument();
    expect(screen.getByTestId('company-logo')).toBeInTheDocument();
    expect(screen.getByText('Grins Irrigation')).toBeInTheDocument();
    expect(screen.getByText('(555) 123-4567')).toBeInTheDocument();
    expect(screen.getByText((_content, element) => element?.tagName === 'H2' && element?.textContent?.includes('EST-001') === true)).toBeInTheDocument();
    expect(screen.getByText('John Smith')).toBeInTheDocument();
  });

  it('renders without crashing when company fields are null and falls back to default name', () => {
    const nullBrandingData: PortalEstimate = {
      ...mockEstimateData,
      company_name: null,
      company_address: null,
      company_phone: null,
      company_logo_url: null,
    };
    mockUsePortalEstimate.mockReturnValue({ data: nullBrandingData, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('estimate-review-page')).toBeInTheDocument();
    expect(screen.queryByTestId('company-logo')).not.toBeInTheDocument();
    // Falls back to the default company name.
    expect(screen.getByText('Grins Irrigation')).toBeInTheDocument();
  });

  it('renders line items table', () => {
    mockUsePortalEstimate.mockReturnValue({ data: mockEstimateData, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('estimate-line-items-table')).toBeInTheDocument();
    expect(screen.getByText('Sprinkler Head')).toBeInTheDocument();
    expect(screen.getByText('Labor')).toBeInTheDocument();
  });

  it('renders totals section', () => {
    mockUsePortalEstimate.mockReturnValue({ data: mockEstimateData, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('estimate-totals')).toBeInTheDocument();
  });

  it('renders notes when present', () => {
    mockUsePortalEstimate.mockReturnValue({ data: mockEstimateData, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByText('Work to be completed within 2 weeks.')).toBeInTheDocument();
  });

  it('renders approve and reject buttons when not readonly', () => {
    mockUsePortalEstimate.mockReturnValue({ data: mockEstimateData, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('approve-estimate-btn')).toBeInTheDocument();
    expect(screen.getByTestId('reject-estimate-btn')).toBeInTheDocument();
  });

  it('shows readonly notice when estimate is already actioned', () => {
    mockUsePortalEstimate.mockReturnValue({
      data: { ...mockEstimateData, is_readonly: true, status: 'APPROVED' },
      isLoading: false,
      error: null,
    });
    renderWithProviders();

    expect(screen.getByTestId('estimate-readonly-notice')).toBeInTheDocument();
    expect(screen.queryByTestId('approve-estimate-btn')).not.toBeInTheDocument();
  });

  it('shows reject form with textarea when reject is clicked', async () => {
    const user = userEvent.setup();
    mockUsePortalEstimate.mockReturnValue({ data: mockEstimateData, isLoading: false, error: null });
    renderWithProviders();

    await user.click(screen.getByTestId('reject-estimate-btn'));
    expect(screen.getByTestId('reject-form')).toBeInTheDocument();
    expect(screen.getByTestId('reject-reason-textarea')).toBeInTheDocument();
  });

  it('calls approve mutation and navigates on approve', async () => {
    const user = userEvent.setup();
    mockApproveEstimate.mockResolvedValue(undefined);
    mockUsePortalEstimate.mockReturnValue({ data: mockEstimateData, isLoading: false, error: null });
    renderWithProviders();

    await user.click(screen.getByTestId('approve-estimate-btn'));
    await waitFor(() => {
      expect(mockApproveEstimate).toHaveBeenCalled();
    });
  });

  it('renders tier options when multi-tier estimate', () => {
    const tieredEstimate: PortalEstimate = {
      ...mockEstimateData,
      tiers: [
        { name: 'good', line_items: [{ item: 'Basic', description: 'Basic service', unit_price: 100, quantity: 1 }], total: 100 },
        { name: 'better', line_items: [{ item: 'Standard', description: 'Standard service', unit_price: 200, quantity: 1 }], total: 200 },
        { name: 'best', line_items: [{ item: 'Premium', description: 'Premium service', unit_price: 300, quantity: 1 }], total: 300 },
      ],
    };
    mockUsePortalEstimate.mockReturnValue({ data: tieredEstimate, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('tier-options')).toBeInTheDocument();
    expect(screen.getByTestId('tier-option-good')).toBeInTheDocument();
    expect(screen.getByTestId('tier-option-better')).toBeInTheDocument();
    expect(screen.getByTestId('tier-option-best')).toBeInTheDocument();
  });

  it('disables approve button when tiers exist but none selected', () => {
    const tieredEstimate: PortalEstimate = {
      ...mockEstimateData,
      tiers: [
        { name: 'good', line_items: [{ item: 'Basic', description: 'Basic', unit_price: 100, quantity: 1 }], total: 100 },
      ],
    };
    mockUsePortalEstimate.mockReturnValue({ data: tieredEstimate, isLoading: false, error: null });
    renderWithProviders();

    expect(screen.getByTestId('approve-estimate-btn')).toBeDisabled();
  });

  it('does not expose internal IDs in the rendered output', () => {
    mockUsePortalEstimate.mockReturnValue({ data: mockEstimateData, isLoading: false, error: null });
    const { container } = renderWithProviders();
    const html = container.innerHTML;

    // No UUID patterns should appear in the rendered HTML
    expect(html).not.toMatch(/customer_id|lead_id|staff_id|job_id/);
  });
});
