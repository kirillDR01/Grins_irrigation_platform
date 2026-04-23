/**
 * Tests for NoReplyReviewQueue (bughunt H-7).
 *
 * Covers:
 *   - renders rows from API data
 *   - Send Reminder opens a confirm dialog with the recipient phone
 *     visible before firing the mutation
 *   - Mark Contacted fires the mutation and invalidates the queue
 *   - empty state renders when no rows
 *
 * Mocks ``appointmentApi`` so no real network I/O happens and, most
 * importantly, no SMS is dispatched.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NoReplyReviewQueue } from './NoReplyReviewQueue';

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
  Toaster: () => null,
}));

vi.mock('../api/appointmentApi', () => ({
  appointmentApi: {
    noReviewList: vi.fn(),
    markContacted: vi.fn(),
    sendReminder: vi.fn(),
  },
}));

import { appointmentApi } from '../api/appointmentApi';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

function makeRow(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 'appt-1',
    job_id: 'job-1',
    staff_id: 'staff-1',
    scheduled_date: '2026-04-25',
    time_window_start: '09:00:00',
    time_window_end: '11:00:00',
    status: 'scheduled',
    needs_review_reason: 'no_confirmation_response',
    confirmation_sent_at: '2026-04-13T10:00:00Z',
    customer_id: 'cust-1',
    customer_name: 'Jane Doe',
    customer_phone: '+19527373312',
    ...overrides,
  };
}

describe('NoReplyReviewQueue (bughunt H-7)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders rows from API data', async () => {
    (appointmentApi.noReviewList as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeRow(),
      makeRow({
        id: 'appt-2',
        customer_name: 'John Smith',
        customer_phone: '+15125550000',
      }),
    ]);

    render(<NoReplyReviewQueue />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('no-reply-row-appt-1')).toBeInTheDocument();
    });
    expect(screen.getByTestId('no-reply-row-appt-2')).toBeInTheDocument();
    expect(screen.getByText('Jane Doe')).toBeInTheDocument();
    expect(screen.getByText('John Smith')).toBeInTheDocument();
    expect(appointmentApi.noReviewList).toHaveBeenCalledWith({
      reason: 'no_confirmation_response',
    });
  });

  it('Send Reminder confirms with recipient preview before firing mutation', async () => {
    (appointmentApi.noReviewList as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeRow(),
    ]);
    (appointmentApi.sendReminder as ReturnType<typeof vi.fn>).mockResolvedValue(
      {
        appointment_id: 'appt-1',
        status: 'scheduled',
        sms_sent: true,
      }
    );

    const user = userEvent.setup();
    render(<NoReplyReviewQueue />, { wrapper: createWrapper() });

    // Click Send Reminder on the row — dialog opens, no SMS fired yet.
    const sendBtn = await screen.findByTestId('send-reminder-btn-appt-1');
    await user.click(sendBtn);

    // The confirm dialog shows the recipient phone prominently.
    const phoneDisplay = await screen.findByTestId('reminder-confirm-phone');
    expect(phoneDisplay).toHaveTextContent('+19527373312');
    const customerDisplay = screen.getByTestId('reminder-confirm-customer');
    expect(customerDisplay).toHaveTextContent('Jane Doe');

    // Crucially: the SMS mutation has NOT fired yet.
    expect(appointmentApi.sendReminder).not.toHaveBeenCalled();

    // Admin confirms — now the mutation fires.
    const confirmBtn = screen.getByTestId('confirm-send-reminder-btn');
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(appointmentApi.sendReminder).toHaveBeenCalledWith('appt-1');
    });
  });

  it('Mark Contacted fires the mutation and invalidates the queue', async () => {
    (appointmentApi.noReviewList as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeRow(),
    ]);
    (
      appointmentApi.markContacted as ReturnType<typeof vi.fn>
    ).mockResolvedValue({ appointment_id: 'appt-1', needs_review_reason: null });

    const user = userEvent.setup();
    render(<NoReplyReviewQueue />, { wrapper: createWrapper() });

    const markBtn = await screen.findByTestId('mark-contacted-btn-appt-1');
    await user.click(markBtn);

    await waitFor(() => {
      expect(appointmentApi.markContacted).toHaveBeenCalledWith('appt-1');
    });

    // The queue list query should be re-fetched after the mutation.
    await waitFor(() => {
      expect(appointmentApi.noReviewList).toHaveBeenCalledTimes(2);
    });
  });

  it('renders the empty state when no rows come back', async () => {
    (appointmentApi.noReviewList as ReturnType<typeof vi.fn>).mockResolvedValue(
      []
    );

    render(<NoReplyReviewQueue />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('no-reply-queue-empty')).toBeInTheDocument();
    });
  });

  it('Refresh button invalidates the queue and re-fetches (Gap 15)', async () => {
    (appointmentApi.noReviewList as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeRow(),
    ]);

    const user = userEvent.setup();
    render(<NoReplyReviewQueue />, { wrapper: createWrapper() });

    const refreshBtn = await screen.findByTestId('refresh-no-reply-btn');
    expect(screen.getByTestId('queue-last-updated')).toBeInTheDocument();

    await waitFor(() => {
      expect(appointmentApi.noReviewList).toHaveBeenCalledTimes(1);
    });

    await user.click(refreshBtn);

    await waitFor(() => {
      expect(appointmentApi.noReviewList).toHaveBeenCalledTimes(2);
    });
  });
});
