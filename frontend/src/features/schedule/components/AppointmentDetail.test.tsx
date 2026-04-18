/**
 * Tests for AppointmentDetail edit wiring (Req 18).
 * Validates: Requirements 18.1, 18.2, 18.3
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { AppointmentDetail } from './AppointmentDetail';
import type { Appointment } from '../types';

// ── Mock data ────────────────────────────────────────────────────────────────

const mockAppointment: Appointment = {
  id: 'appt-001',
  job_id: 'job-001',
  staff_id: 'staff-001',
  scheduled_date: '2025-07-15',
  time_window_start: '09:00:00',
  time_window_end: '11:00:00',
  status: 'confirmed',
  arrived_at: null,
  en_route_at: null,
  completed_at: null,
  notes: 'Check backflow preventer',
  route_order: 1,
  estimated_arrival: '09:15:00',
  created_at: '2025-07-10T12:00:00Z',
  updated_at: '2025-07-10T12:00:00Z',
  job_type: 'spring_startup',
  customer_name: 'Jane Smith',
  staff_name: 'Mike T',
};

const mockJob = {
  id: 'job-001',
  customer_id: 'cust-001',
  job_type: 'spring_startup',
  status: 'scheduled',
  materials_required: ['PVC pipe', 'Sprinkler heads'],
  estimated_duration_minutes: 90,
};

const mockCustomer = {
  id: 'cust-001',
  first_name: 'Jane',
  last_name: 'Smith',
  phone: '612-555-9876',
  email: 'jane@example.com',
  properties: [
    {
      is_primary: true,
      address: '123 Elm St',
      city: 'Eden Prairie',
      state: 'MN',
      zip_code: '55344',
    },
  ],
};

// ── Mock hooks ───────────────────────────────────────────────────────────────

const mockUseAppointment = vi.fn();
const mockConfirmMutateAsync = vi.fn();
const mockCancelMutateAsync = vi.fn();
const mockNoShowMutateAsync = vi.fn();

vi.mock('../hooks/useAppointments', () => ({
  useAppointment: (...args: unknown[]) => mockUseAppointment(...args),
  appointmentKeys: {
    all: ['appointments'] as const,
    lists: () => ['appointments', 'list'] as const,
    list: (params?: unknown) => ['appointments', 'list', params] as const,
    details: () => ['appointments', 'detail'] as const,
    detail: (id: string) => ['appointments', 'detail', id] as const,
    daily: (date: string) => ['appointments', 'daily', date] as const,
    weekly: (s?: string, e?: string) => ['appointments', 'weekly', s, e] as const,
  },
}));

vi.mock('../hooks/useAppointmentMutations', () => ({
  useConfirmAppointment: () => ({
    mutateAsync: mockConfirmMutateAsync,
    isPending: false,
  }),
  useCancelAppointment: () => ({
    mutateAsync: mockCancelMutateAsync,
    isPending: false,
  }),
  useMarkAppointmentNoShow: () => ({
    mutateAsync: mockNoShowMutateAsync,
    isPending: false,
  }),
  useSendConfirmation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

vi.mock('@/features/jobs/api/jobApi', () => ({
  jobApi: {
    get: vi.fn().mockResolvedValue({
      id: 'job-001',
      customer_id: 'cust-001',
      job_type: 'spring_startup',
      status: 'scheduled',
      materials_required: ['PVC pipe', 'Sprinkler heads'],
      estimated_duration_minutes: 90,
    }),
    getByCustomer: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  },
}));

vi.mock('@/features/customers/api/customerApi', () => ({
  customerApi: {
    get: vi.fn().mockResolvedValue({
      id: 'cust-001',
      first_name: 'Jane',
      last_name: 'Smith',
      phone: '612-555-9876',
      email: 'jane@example.com',
      properties: [
        {
          is_primary: true,
          address: '123 Elm St',
          city: 'Eden Prairie',
          state: 'MN',
          zip_code: '55344',
        },
      ],
    }),
  },
}));

// Mock sub-components that aren't relevant to edit wiring tests
vi.mock('./StaffWorkflowButtons', () => ({
  StaffWorkflowButtons: () => <div data-testid="staff-workflow-buttons" />,
}));
vi.mock('./PaymentCollector', () => ({
  PaymentCollector: () => <div data-testid="payment-collector" />,
}));
vi.mock('./InvoiceCreator', () => ({
  InvoiceCreator: () => <div data-testid="invoice-creator" />,
}));
vi.mock('./EstimateCreator', () => ({
  EstimateCreator: () => <div data-testid="estimate-creator" />,
}));
vi.mock('./AppointmentNotes', () => ({
  AppointmentNotes: () => <div data-testid="appointment-notes" />,
}));
vi.mock('./ReviewRequest', () => ({
  ReviewRequest: () => <div data-testid="review-request" />,
}));

// ── Helpers ──────────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

function setupDefaultMocks() {
  mockUseAppointment.mockReturnValue({
    data: mockAppointment,
    isLoading: false,
    error: null,
  });
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe('AppointmentDetail — Edit Wiring (Req 18)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupDefaultMocks();
  });

  it('renders the Edit button with data-testid="edit-btn"', async () => {
    render(
      <AppointmentDetail appointmentId="appt-001" />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('edit-btn')).toBeInTheDocument();
    });
  });

  it('clicking Edit button calls onEdit with the correct appointment data (Req 18.1)', async () => {
    const onEdit = vi.fn();
    const user = userEvent.setup();

    render(
      <AppointmentDetail appointmentId="appt-001" onEdit={onEdit} />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('edit-btn')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('edit-btn'));

    expect(onEdit).toHaveBeenCalledTimes(1);
    expect(onEdit).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'appt-001',
        job_id: 'job-001',
        staff_id: 'staff-001',
        scheduled_date: '2025-07-15',
        time_window_start: '09:00:00',
        time_window_end: '11:00:00',
        notes: 'Check backflow preventer',
      }),
    );
  });

  it('Edit button is safe to click when onEdit is not provided', async () => {
    const user = userEvent.setup();

    render(
      <AppointmentDetail appointmentId="appt-001" />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('edit-btn')).toBeInTheDocument();
    });

    // Should not throw
    await user.click(screen.getByTestId('edit-btn'));
  });

  it('does not render Edit button for terminal (completed) appointments', async () => {
    mockUseAppointment.mockReturnValue({
      data: { ...mockAppointment, status: 'completed' },
      isLoading: false,
      error: null,
    });

    render(
      <AppointmentDetail appointmentId="appt-001" />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('appointment-detail')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('edit-btn')).not.toBeInTheDocument();
  });

  it('does not render Edit button for cancelled appointments', async () => {
    mockUseAppointment.mockReturnValue({
      data: { ...mockAppointment, status: 'cancelled' },
      isLoading: false,
      error: null,
    });

    render(
      <AppointmentDetail appointmentId="appt-001" />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('appointment-detail')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('edit-btn')).not.toBeInTheDocument();
  });

  it('displays appointment date, time, and notes in the detail view (Req 18.2)', async () => {
    render(
      <AppointmentDetail appointmentId="appt-001" />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('appointment-detail')).toBeInTheDocument();
    });

    // Date is rendered
    expect(screen.getByText(/July 15, 2025/i)).toBeInTheDocument();
    // Time window is rendered
    expect(screen.getByText(/09:00 - 11:00/)).toBeInTheDocument();
    // Notes are rendered
    expect(screen.getByText('Check backflow preventer')).toBeInTheDocument();
  });

  it('displays staff name in the detail view (Req 18.2)', async () => {
    render(
      <AppointmentDetail appointmentId="appt-001" />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('appointment-detail')).toBeInTheDocument();
    });

    expect(screen.getByText('Mike T')).toBeInTheDocument();
  });

  it('passes full appointment object to onEdit for pre-populating the edit form (Req 18.2)', async () => {
    const onEdit = vi.fn();
    const user = userEvent.setup();

    render(
      <AppointmentDetail appointmentId="appt-001" onEdit={onEdit} />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('edit-btn')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('edit-btn'));

    // The full appointment object is passed so AppointmentForm can pre-populate
    const passedAppointment = onEdit.mock.calls[0][0];
    expect(passedAppointment.scheduled_date).toBe('2025-07-15');
    expect(passedAppointment.time_window_start).toBe('09:00:00');
    expect(passedAppointment.time_window_end).toBe('11:00:00');
    expect(passedAppointment.job_id).toBe('job-001');
    expect(passedAppointment.staff_id).toBe('staff-001');
    expect(passedAppointment.notes).toBe('Check backflow preventer');
  });

  it('shows loading state while appointment is being fetched', () => {
    mockUseAppointment.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(
      <AppointmentDetail appointmentId="appt-001" />,
      { wrapper: createWrapper() },
    );

    // Should not show edit button while loading
    expect(screen.queryByTestId('edit-btn')).not.toBeInTheDocument();
  });

  it('shows error state when appointment fetch fails', () => {
    mockUseAppointment.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
    });

    render(
      <AppointmentDetail appointmentId="appt-001" />,
      { wrapper: createWrapper() },
    );

    expect(screen.getByText(/error loading appointment/i)).toBeInTheDocument();
    expect(screen.queryByTestId('edit-btn')).not.toBeInTheDocument();
  });
});

// bughunt M-1: AppointmentDetail must render the canonical
// SendConfirmationButton when the appointment is in DRAFT — admins
// drilling into a draft from the detail modal previously had to back
// out to the calendar card to send.
describe('AppointmentDetail — Send Confirmation button (bughunt M-1)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders SendConfirmationButton for DRAFT appointments', async () => {
    mockUseAppointment.mockReturnValue({
      data: { ...mockAppointment, status: 'draft' },
      isLoading: false,
      error: null,
    });

    render(<AppointmentDetail appointmentId="appt-001" />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(
        screen.getByTestId('send-confirmation-btn-appt-001'),
      ).toBeInTheDocument();
    });
  });

  // Regression: the initial M-1 fix called
  // <SendConfirmationButton appointmentId={appointmentId} /> but the canonical
  // button's prop is `appointment: Appointment`. With appointmentId passed
  // instead, `appointment` was undefined and `appointment.status` threw
  // "can't access property 'status', appointment is undefined" — which
  // surfaced on Vercel every time an admin clicked a draft job on the
  // schedule. This test pins the prop shape so the regression can't come
  // back.
  it('passes the appointment object (not the id) to SendConfirmationButton', async () => {
    const draftAppt = { ...mockAppointment, status: 'draft' as const };
    mockUseAppointment.mockReturnValue({
      data: draftAppt,
      isLoading: false,
      error: null,
    });

    render(<AppointmentDetail appointmentId="appt-001" />, {
      wrapper: createWrapper(),
    });

    // The canonical button reads appointment.customer_name for its tooltip;
    // if we passed an id string instead of the object, the render crashes
    // before this assertion and the test fails.
    const btn = await screen.findByTestId('send-confirmation-btn-appt-001');
    expect(btn).toHaveAttribute(
      'title',
      `Send confirmation SMS to ${draftAppt.customer_name}`,
    );
  });

  it('does not render SendConfirmationButton for non-DRAFT statuses', async () => {
    mockUseAppointment.mockReturnValue({
      data: { ...mockAppointment, status: 'confirmed' },
      isLoading: false,
      error: null,
    });

    render(<AppointmentDetail appointmentId="appt-001" />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(screen.getByTestId('appointment-detail')).toBeInTheDocument();
    });

    expect(
      screen.queryByTestId('send-confirmation-btn-appt-001'),
    ).not.toBeInTheDocument();
  });
});
