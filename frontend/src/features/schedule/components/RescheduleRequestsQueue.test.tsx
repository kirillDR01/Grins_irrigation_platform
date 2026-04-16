/**
 * Tests for RescheduleRequestsQueue (bughunt H-6).
 *
 * Verifies that when an admin picks a new date via the reschedule dialog,
 * the UI calls the new ``/reschedule-from-request`` endpoint (NOT the
 * generic update-appointment endpoint) and shows the
 * "customer will receive a new confirmation request" success toast.
 *
 * Mocks the SMS provider — the backend path is already unit/functional
 * tested to restart the Y/R/C cycle. This test only checks the FE wiring.
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

// The form uses these hooks; stub them to avoid pulling in jobs/staff loaders.
vi.mock('@/features/jobs/hooks', () => ({
  useJobsReadyToSchedule: () => ({ data: { items: [] }, isLoading: false }),
}));
vi.mock('@/features/staff/hooks', () => ({
  useStaff: () => ({
    data: {
      items: [
        { id: '11111111-2222-3333-4444-555555555555', name: 'Alice', role: 'tech' },
      ],
    },
    isLoading: false,
  }),
}));
vi.mock('@/features/jobs/api/jobApi', () => ({
  jobApi: {
    get: vi.fn().mockResolvedValue({ id: 'job-1', customer_id: 'cust-1' }),
  },
}));
vi.mock('@/features/customers/api/customerApi', () => ({
  customerApi: {
    get: vi.fn().mockResolvedValue({
      id: 'cust-1',
      properties: [],
    }),
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
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
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
    job_id: 'job-1',
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
    (rescheduleApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeRequest(),
    ]);
    (rescheduleApi.resolve as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 'req-1',
      status: 'resolved',
    });
    (appointmentApi.getById as ReturnType<typeof vi.fn>).mockResolvedValue(
      makeAppointment(),
    );
    (
      appointmentApi.rescheduleFromRequest as ReturnType<typeof vi.fn>
    ).mockResolvedValue(
      makeAppointment({
        scheduled_date: '2026-04-23',
        time_window_start: '14:00:00',
        time_window_end: '16:00:00',
      }),
    );
  });

  it('calls the reschedule-from-request endpoint when admin picks a new date', async () => {
    const user = userEvent.setup();
    render(<RescheduleRequestsQueue />, { wrapper: createWrapper() });

    // The row with the reschedule button appears after the list loads.
    const resBtn = await screen.findByTestId('reschedule-to-alternative-btn');
    await user.click(resBtn);

    // The AppointmentForm dialog opens — wait for the date input
    // (fetched via useAppointment).
    const dateInput = await screen.findByTestId('date-input');
    // Re-set scheduled_date to the new value.
    await user.clear(dateInput);
    await user.type(dateInput, '2026-04-23');

    // Start/end times — re-set them.
    const startInput = screen.getByTestId('start-time-input');
    await user.clear(startInput);
    await user.type(startInput, '14:00');
    const endInput = screen.getByTestId('end-time-input');
    await user.clear(endInput);
    await user.type(endInput, '16:00');

    // Submit: button label is "Send Reschedule" (submitLabel override).
    const submit = screen.getByTestId('submit-btn');
    expect(submit).toHaveTextContent('Send Reschedule');
    await user.click(submit);

    await waitFor(() => {
      expect(appointmentApi.rescheduleFromRequest).toHaveBeenCalledTimes(1);
    });

    // Generic update must NOT be called on this path.
    expect(appointmentApi.update).not.toHaveBeenCalled();

    // The call routes to the new endpoint with an ISO timestamp payload.
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

    const dateInput = await screen.findByTestId('date-input');
    await user.clear(dateInput);
    await user.type(dateInput, '2026-04-23');
    const startInput = screen.getByTestId('start-time-input');
    await user.clear(startInput);
    await user.type(startInput, '14:00');
    const endInput = screen.getByTestId('end-time-input');
    await user.clear(endInput);
    await user.type(endInput, '16:00');

    await user.click(screen.getByTestId('submit-btn'));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        expect.stringContaining('customer will receive a new confirmation request'),
      );
    });
  });
});
