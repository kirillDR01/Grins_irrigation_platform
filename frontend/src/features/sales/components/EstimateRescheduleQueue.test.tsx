/**
 * Tests for EstimateRescheduleQueue.
 *
 * Mirror of RescheduleRequestsQueue.test.tsx, scoped to the sales-side
 * queue. Covers the empty / loading / populated render branches and the
 * Resolve action's wiring through to ``salesRescheduleApi.resolve``.
 *
 * Validates: sales-pipeline-estimate-visit-confirmation-lifecycle Task 19.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { toast } from 'sonner';
import { EstimateRescheduleQueue } from './EstimateRescheduleQueue';

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
  Toaster: () => null,
}));

vi.mock('../api/salesRescheduleApi', () => ({
  salesRescheduleApi: {
    list: vi.fn(),
    resolve: vi.fn(),
    rescheduleFromRequest: vi.fn(),
  },
}));

import { salesRescheduleApi } from '../api/salesRescheduleApi';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });
  // eslint-disable-next-line react/display-name
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

const fixtureRequest = {
  id: 'rq-1',
  job_id: null,
  appointment_id: null,
  sales_calendar_event_id: 'sce-1',
  customer_id: 'cust-1',
  customer_name: 'Jane Doe',
  original_appointment_date: '2026-05-12',
  original_appointment_staff: null,
  requested_alternatives: null,
  raw_alternatives_text: 'Tuesday at 3 or Wednesday morning',
  status: 'open' as const,
  created_at: new Date().toISOString(),
  resolved_at: null,
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('EstimateRescheduleQueue', () => {
  it('renders nothing when there are no open requests', async () => {
    vi.mocked(salesRescheduleApi.list).mockResolvedValueOnce([]);
    const { container } = render(<EstimateRescheduleQueue />, {
      wrapper: createWrapper(),
    });
    await waitFor(() => {
      expect(salesRescheduleApi.list).toHaveBeenCalledWith('open');
    });
    // Empty queue collapses entirely so the page doesn't accumulate empty headers.
    await waitFor(() => {
      expect(container).toBeEmptyDOMElement();
    });
  });

  it('shows the customer-suggested dates inline on each card', async () => {
    vi.mocked(salesRescheduleApi.list).mockResolvedValueOnce([fixtureRequest]);
    render(<EstimateRescheduleQueue />, { wrapper: createWrapper() });

    await screen.findByText('Jane Doe');
    expect(screen.getByText(/Estimate Reschedule Requests \(1\)/)).toBeInTheDocument();
    expect(
      screen.getByTestId(`estimate-reschedule-alternatives-${fixtureRequest.id}`),
    ).toHaveTextContent('Tuesday at 3 or Wednesday morning');
  });

  it('clicking Resolve calls salesRescheduleApi.resolve and toasts on success', async () => {
    vi.mocked(salesRescheduleApi.list).mockResolvedValue([fixtureRequest]);
    vi.mocked(salesRescheduleApi.resolve).mockResolvedValueOnce({
      ...fixtureRequest,
      status: 'resolved',
      resolved_at: new Date().toISOString(),
    });

    const user = userEvent.setup();
    render(<EstimateRescheduleQueue />, { wrapper: createWrapper() });

    const resolveBtn = await screen.findByTestId(
      `estimate-reschedule-resolve-${fixtureRequest.id}`,
    );
    await user.click(resolveBtn);

    await waitFor(() => {
      expect(salesRescheduleApi.resolve).toHaveBeenCalledWith(fixtureRequest.id);
    });
    expect(toast.success).toHaveBeenCalledWith('Reschedule request resolved');
  });

  it('shows an error message when the list query fails', async () => {
    vi.mocked(salesRescheduleApi.list).mockRejectedValueOnce(
      new Error('boom'),
    );
    render(<EstimateRescheduleQueue />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(
        screen.getByText(/Could not load estimate reschedule requests/),
      ).toBeInTheDocument();
    });
  });
});
