import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { EstimateReview } from './EstimateReview';
import { ApprovalConfirmation } from './ApprovalConfirmation';
import type { PortalEstimate } from '../types';

// F5 regression guard: this test mirrors the *production* portal route table
// (estimates/:token AND estimates/:token/confirmed). If the production router
// drops the `confirmed` child route, clicking Approve will land on an
// unregistered URL and the test fails — exactly the bug F5 closes.

const baseEstimate: PortalEstimate = {
  company_name: "Grin's Irrigation",
  company_logo_url: null,
  company_address: null,
  company_phone: null,
  customer_name: 'Approval Test',
  estimate_number: 'EST-APR-001',
  status: 'SENT',
  line_items: [
    { item: 'Service', description: 'Test', unit_price: 100, quantity: 1 },
  ],
  tiers: null,
  subtotal: 100,
  tax_amount: 0,
  discount_amount: 0,
  total: 100,
  promotion_code: null,
  notes: null,
  valid_until: null,
  created_at: '2026-05-04T10:00:00Z',
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
    isError: false,
    error: null,
  }),
  useRejectEstimate: () => ({
    mutateAsync: mockRejectEstimate,
    isPending: false,
    isError: false,
    error: null,
  }),
}));

function renderWithProductionRoutes(token = 'tok-approval-123') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/portal/estimates/${token}`]}>
        <Routes>
          <Route path="/portal/estimates/:token" element={<EstimateReview />} />
          <Route
            path="/portal/estimates/:token/confirmed"
            element={<ApprovalConfirmation />}
          />
          <Route
            path="/portal/contracts/:token/confirmed"
            element={<ApprovalConfirmation />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('EstimateReview approval → confirmed navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApproveEstimate.mockResolvedValue(undefined);
    mockRejectEstimate.mockResolvedValue(undefined);
    mockUsePortalEstimate.mockReturnValue({
      data: baseEstimate,
      isLoading: false,
      error: null,
    });
  });

  it('navigates to /portal/estimates/:token/confirmed and renders the confirmation page on Approve', async () => {
    const user = userEvent.setup();
    renderWithProductionRoutes();

    await user.click(screen.getByTestId('approve-estimate-btn'));

    await waitFor(() => {
      expect(mockApproveEstimate).toHaveBeenCalled();
    });
    expect(
      await screen.findByTestId('approval-confirmation-page'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('confirmation-title')).toHaveTextContent(
      'Estimate Approved',
    );
  });

  it('navigates to confirmed page on Reject', async () => {
    const user = userEvent.setup();
    renderWithProductionRoutes();

    await user.click(screen.getByTestId('reject-estimate-btn'));
    await user.click(screen.getByTestId('confirm-reject-btn'));

    await waitFor(() => {
      expect(mockRejectEstimate).toHaveBeenCalled();
    });
    expect(
      await screen.findByTestId('approval-confirmation-page'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('confirmation-title')).toHaveTextContent(
      'Estimate Declined',
    );
  });
});
