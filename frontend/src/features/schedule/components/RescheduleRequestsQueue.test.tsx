/**
 * Tests for RescheduleRequestsQueue (bughunt H-6).
 *
 * Verifies that when an admin picks a new date via the reschedule dialog,
 * the UI calls the new ``/reschedule-from-request`` endpoint (NOT the
 * generic update-appointment endpoint) and shows the
 * "customer will receive a new confirmation request" success toast.
 *
 * We stub ``AppointmentForm`` with a tiny test double so we exercise the
 * queue's wiring (click → dialog → submitOverride → mutation → API) without
 * driving the full react-hook-form + Radix Dialog + JobSelectorCombobox
 * chain, which does not reliably flush in jsdom. The real form is covered
 * by its own component tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { toast } from 'sonner';
import { RescheduleRequestsQueue } from './RescheduleRequestsQueue';

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
  Toaster: () => null,
}));

vi.mock('../api/appointmentApi', () => ({
  appointmentApi: {
    getById: vi.fn(),
    update: vi.fn(),
    rescheduleFromRequest: vi.fn(),
  },
}));

vi.mock('../api/rescheduleApi', () => ({
  rescheduleApi: {
    list: vi.fn(),
    resolve: vi.fn(),
  },
}));

// Stub AppointmentForm: render a submit button that fires submitOverride
// with a canned payload. This keeps the test focused on the queue's wiring
// to useRescheduleFromRequest + appointmentApi.rescheduleFromRequest.
vi.mock('./AppointmentForm', () => ({
  AppointmentForm: ({
    submitOverride,
    submitLabel,
    onSuccess,
    onCancel,
  }: {
    submitOverride?: (payload: {
      scheduled_date: string;
      time_window_start: string;
      time_window_end: string;
      staff_id: string;
      notes?: string;
    }) => Promise<void>;
    submitLabel?: string;
    onSuccess?: () => void;
    onCancel?: () => void;
  }) => {
    const handleSubmit = async () => {
      try {
        await submitOverride?.({
          scheduled_date: '2026-04-23',
          time_window_start: '14:00',
          time_window_end: '16:00',
          staff_id: '11111111-2222-3333-4444-555555555555',
        });
        onSuccess?.();
      } catch {
        // submitOverride re-throws on mutation failure; swallow so the
        // promise rejection doesn't reach React and break the test harness.
        // The error toast is already fired inside handleRescheduleSubmit.
      }
    };
    return (
      <div data-testid="mock-appointment-form">
        <button data-testid="submit-btn" onClick={handleSubmit} type="button">
          {submitLabel ?? 'Save'}
        </button>
        <button data-testid="cancel-btn" onClick={onCancel} type="button">
          Cancel
        </button>
      </div>
    );
  },
}));

import { appointmentApi } from '../api/appointmentApi';
import { rescheduleApi } from '../api/rescheduleApi';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function makeRequest(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 'req-1',
    job_id: 'job-1',
    appointment_id: 'appt-1',
    customer_id: 'cust-1',
    customer_name: 'Jane Smith',
    original_appointment_date: '2026-04-20',
    original_appointment_staff: 'Alice',
    requested_alternatives: null,
    raw_alternatives_text: 'next Friday afternoon',
    status: 'open',
    created_at: '2026-04-16T10:00:00Z',
    resolved_at: null,
    ...overrides,
  };
}

function makeAppointment(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 'appt-1',
    job_id: '99999999-aaaa-bbbb-cccc-dddddddddddd',
    staff_id: '11111111-2222-3333-4444-555555555555',
    scheduled_date: '2026-04-20',
    time_window_start: '09:00:00',
    time_window_end: '11:00:00',
    status: 'scheduled',
    arrived_at: null,
    en_route_at: null,
    completed_at: null,
    notes: null,
    route_order: 1,
    estimated_arrival: null,
    created_at: '2026-04-16T10:00:00Z',
    updated_at: '2026-04-16T10:00:00Z',
    job_type: 'Spring Turn-On',
    customer_name: 'Jane Smith',
    staff_name: 'Alice',
    service_agreement_id: null,
    ...overrides,
  };
}

describe('RescheduleRequestsQueue (bughunt H-6)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (rescheduleApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([makeRequest()]);
    (rescheduleApi.resolve as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 'req-1',
      status: 'resolved',
    });
    (appointmentApi.getById as ReturnType<typeof vi.fn>).mockResolvedValue(
      makeAppointment()
    );
    (appointmentApi.rescheduleFromRequest as ReturnType<typeof vi.fn>).mockResolvedValue(
      makeAppointment({
        scheduled_date: '2026-04-23',
        time_window_start: '14:00:00',
        time_window_end: '16:00:00',
      })
    );
  });

  it('calls the reschedule-from-request endpoint when admin picks a new date', async () => {
    const user = userEvent.setup();
    render(<RescheduleRequestsQueue />, { wrapper: createWrapper() });

    const resBtn = await screen.findByTestId('reschedule-to-alternative-btn');
    await user.click(resBtn);

    // The (mocked) AppointmentForm mounts. Its submit button fires
    // submitOverride with the canned payload (2026-04-23, 14:00, 16:00,
    // the valid staff UUID).
    const submit = await screen.findByTestId('submit-btn');
    expect(submit).toHaveTextContent('Send Reschedule');
    await user.click(submit);

    await waitFor(() => {
      expect(appointmentApi.rescheduleFromRequest).toHaveBeenCalledTimes(1);
    });

    // Generic update must NOT be called on this path.
    expect(appointmentApi.update).not.toHaveBeenCalled();

    // The call routes to the new endpoint with an ISO timestamp payload
    // composed from scheduled_date + time_window_start.
    const [calledId, calledPayload] = (
      appointmentApi.rescheduleFromRequest as ReturnType<typeof vi.fn>
    ).mock.calls[0];
    expect(calledId).toBe('appt-1');
    expect(calledPayload).toEqual({
      new_scheduled_at: '2026-04-23T14:00:00',
    });
  });

  it('shows the "customer will receive a new confirmation request" success toast', async () => {
    const user = userEvent.setup();
    render(<RescheduleRequestsQueue />, { wrapper: createWrapper() });

    const resBtn = await screen.findByTestId('reschedule-to-alternative-btn');
    await user.click(resBtn);

    const submit = await screen.findByTestId('submit-btn');
    await user.click(submit);

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        expect.stringContaining('customer will receive a new confirmation request')
      );
    });
  });

  it('Refresh button invalidates the query and re-fetches (Gap 15)', async () => {
    const user = userEvent.setup();
    render(<RescheduleRequestsQueue />, { wrapper: createWrapper() });

    const refreshBtn = await screen.findByTestId('refresh-reschedule-btn');
    expect(screen.getByTestId('queue-last-updated')).toBeInTheDocument();

    await waitFor(() => {
      expect(rescheduleApi.list).toHaveBeenCalledTimes(1);
    });

    await user.click(refreshBtn);

    await waitFor(() => {
      expect(rescheduleApi.list).toHaveBeenCalledTimes(2);
    });
  });

  // 2026-05-05 UX upgrade — surface customer-supplied date alternatives
  // inline on the queue card so admins do not have to bounce to Inbound
  // Triage to read "Tue 2pm or Wed 3pm" after the original "R".
  it('renders the latest customer-supplied alternative text on the card', async () => {
    (rescheduleApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeRequest({
        requested_alternatives: {
          entries: [
            { text: 'Monday 9am', at: '2026-04-16T10:05:00Z' },
            { text: 'Tuesday 2pm or Wednesday 3:00pm', at: '2026-04-16T11:00:00Z' },
          ],
        },
      }),
    ]);

    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <RescheduleRequestsQueue />
      </Wrapper>
    );

    const altLine = await screen.findByTestId('reschedule-latest-alternative');
    // Most recent entry wins.
    expect(altLine.textContent).toContain('Tuesday 2pm or Wednesday 3:00pm');
    // Older entries are surfaced via a "(+N earlier)" tail counter.
    expect(altLine.textContent).toContain('+1 earlier');
  });

  it('omits the alternative line when no entries[] are present', async () => {
    (rescheduleApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeRequest({ requested_alternatives: null }),
    ]);

    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <RescheduleRequestsQueue />
      </Wrapper>
    );

    await screen.findByTestId('reschedule-customer-name');
    expect(screen.queryByTestId('reschedule-latest-alternative')).not.toBeInTheDocument();
  });

  // Regression guard for the scrollable-body fix:
  // RescheduleRequestsQueue's reschedule dialog must wrap the form in a
  // flex-1, min-h-0, overflow-y-auto div so the modal scrolls when its
  // content exceeds viewport height. min-h-0 is required for flex children
  // to permit inner scrolling — easy to forget, silently breaks scroll.
  it('wraps the reschedule form in a scrollable body with min-h-0 and overflow-y-auto', async () => {
    const user = userEvent.setup();
    render(<RescheduleRequestsQueue />, { wrapper: createWrapper() });

    const resBtn = await screen.findByTestId('reschedule-to-alternative-btn');
    await user.click(resBtn);

    // Wait for the (mocked) AppointmentForm to mount, which proves the
    // dialog and its body have rendered.
    await screen.findByTestId('mock-appointment-form');

    const scrollBody = screen.getByTestId('reschedule-dialog-scroll-body');
    expect(scrollBody.className).toContain('overflow-y-auto');
    expect(scrollBody.className).toContain('flex-1');
    expect(scrollBody.className).toContain('min-h-0');

    // The form must be a descendant of the scroll body (not a sibling).
    expect(scrollBody).toContainElement(screen.getByTestId('mock-appointment-form'));
  });
});
