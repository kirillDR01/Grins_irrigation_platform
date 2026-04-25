/**
 * Tests for AppointmentModal — container, ARIA, focus, conditional rendering.
 * Validates: Requirements 1.5, 1.6, 2.6, 11.5, 16.2
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppointmentModal } from './AppointmentModal';
import type { Appointment, AppointmentStatus } from '../../types';

// ── Mock data ────────────────────────────────────────────────────────────────

const baseAppointment: Appointment = {
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
  notes: 'Test notes',
  route_order: 1,
  estimated_arrival: '09:15:00',
  created_at: '2025-07-10T12:00:00Z',
  updated_at: '2025-07-10T12:00:00Z',
  job_type: 'spring_startup',
  customer_name: 'Jane Smith',
  staff_name: 'Mike T',
  service_agreement_id: null,
};

const mockJob = {
  id: 'job-001',
  customer_id: 'cust-001',
  job_type: 'spring_startup',
  status: 'scheduled',
  materials_required: ['PVC pipe', 'Sprinkler heads'],
  estimated_duration_minutes: 90,
  description: 'Spring startup service',
  priority_level: 'normal',
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
      property_type: 'Residential',
      address: '123 Elm St',
      city: 'Eden Prairie',
      state: 'MN',
      zip_code: '55344',
      latitude: null,
      longitude: null,
    },
  ],
};

const mockTimeline = {
  appointment_id: 'appt-001',
  events: [],
  pending_reschedule_request: null,
  needs_review_reason: null,
  opt_out: null,
  last_event_at: null,
};

// ── Mock hooks ───────────────────────────────────────────────────────────────

const mockUseAppointment = vi.fn();
const mockUseAppointmentTimeline = vi.fn();
const mockCancelMutateAsync = vi.fn();
const mockNoShowMutateAsync = vi.fn();
const mockResolveRescheduleMutateAsync = vi.fn();
const mockRescheduleFromRequestMutateAsync = vi.fn();
const mockMarkContactedMutateAsync = vi.fn();
const mockSendReminderMutateAsync = vi.fn();
const mockEnRouteMutate = vi.fn();
const mockArrivedMutate = vi.fn();
const mockCompletedMutate = vi.fn();

vi.mock('../../hooks/useAppointments', () => ({
  useAppointment: (...args: unknown[]) => mockUseAppointment(...args),
  appointmentKeys: {
    all: ['appointments'] as const,
    lists: () => ['appointments', 'list'] as const,
    list: (params?: unknown) => ['appointments', 'list', params] as const,
    details: () => ['appointments', 'detail'] as const,
    detail: (id: string) => ['appointments', 'detail', id] as const,
    daily: (date: string) => ['appointments', 'daily', date] as const,
    weekly: (s?: string, e?: string) => ['appointments', 'weekly', s, e] as const,
    timeline: (id: string) => ['appointments', 'timeline', id] as const,
  },
}));

vi.mock('../../hooks/useAppointmentTimeline', () => ({
  useAppointmentTimeline: (...args: unknown[]) => mockUseAppointmentTimeline(...args),
}));

vi.mock('../../hooks/useRescheduleRequests', () => ({
  useResolveRescheduleRequest: () => ({
    mutateAsync: mockResolveRescheduleMutateAsync,
    mutate: mockResolveRescheduleMutateAsync,
    isPending: false,
  }),
}));

vi.mock('../../hooks/useNoReplyReview', () => ({
  useMarkContacted: () => ({
    mutateAsync: mockMarkContactedMutateAsync,
    isPending: false,
  }),
  useSendReminder: () => ({
    mutateAsync: mockSendReminderMutateAsync,
    isPending: false,
  }),
}));

vi.mock('../../hooks/useAppointmentMutations', () => ({
  useCancelAppointment: () => ({
    mutateAsync: mockCancelMutateAsync,
    isPending: false,
  }),
  useMarkAppointmentNoShow: () => ({
    mutateAsync: mockNoShowMutateAsync,
    isPending: false,
  }),
  useRescheduleFromRequest: () => ({
    mutateAsync: mockRescheduleFromRequestMutateAsync,
    isPending: false,
  }),
  useMarkAppointmentEnRoute: () => ({
    mutate: mockEnRouteMutate,
    isPending: false,
  }),
  useMarkAppointmentArrived: () => ({
    mutate: mockArrivedMutate,
    isPending: false,
  }),
  useMarkAppointmentCompleted: () => ({
    mutate: mockCompletedMutate,
    isPending: false,
  }),
}));

vi.mock('../../hooks/useCustomerTags', () => ({
  useCustomerTags: () => ({ data: [], isLoading: false, error: null }),
  customerTagKeys: {
    all: ['customer-tags'] as const,
    byCustomer: (id: string) => ['customer-tags', id] as const,
  },
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
      description: 'Spring startup service',
      priority_level: 'normal',
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
          property_type: 'Residential',
          address: '123 Elm St',
          city: 'Eden Prairie',
          state: 'MN',
          zip_code: '55344',
          latitude: null,
          longitude: null,
        },
      ],
    }),
    getTags: vi.fn().mockResolvedValue([]),
  },
}));

// Mock sub-components that aren't relevant to these tests
vi.mock('../AppointmentCommunicationTimeline', () => ({
  AppointmentCommunicationTimeline: () => <div data-testid="communication-timeline" />,
}));
vi.mock('../AppointmentForm', () => ({
  AppointmentForm: () => <div data-testid="appointment-form" />,
}));
vi.mock('../CancelAppointmentDialog', () => ({
  CancelAppointmentDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="cancel-dialog" /> : null,
}));
vi.mock('../SendConfirmationButton', () => ({
  SendConfirmationButton: () => <div data-testid="send-confirmation-btn" />,
}));
vi.mock('@/shared/components', () => ({
  OptOutBadge: () => <div data-testid="opt-out-badge" />,
}));
vi.mock('./TagEditorSheet', () => ({
  TagEditorSheet: () => <div data-testid="tag-editor-sheet" />,
}));
vi.mock('./PaymentSheetWrapper', () => ({
  PaymentSheetWrapper: () => <div data-testid="payment-sheet" />,
}));
vi.mock('./EstimateSheetWrapper', () => ({
  EstimateSheetWrapper: () => <div data-testid="estimate-sheet" />,
}));
vi.mock('./ReviewConfirmDialog', () => ({
  ReviewConfirmDialog: ({
    open,
    customerName,
    customerPhone,
  }: {
    open: boolean;
    customerName: string;
    customerPhone: string | null;
  }) =>
    open ? (
      <div
        data-testid="review-confirm-dialog"
        data-customer-name={customerName}
        data-customer-phone={customerPhone ?? ''}
      />
    ) : null,
}));

// ── Helpers ──────────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function setupMocks(overrides?: Partial<Appointment>) {
  const appointment = { ...baseAppointment, ...overrides };
  mockUseAppointment.mockReturnValue({
    data: appointment,
    isLoading: false,
    error: null,
    dataUpdatedAt: Date.now(),
    isFetching: false,
  });
  mockUseAppointmentTimeline.mockReturnValue({
    data: mockTimeline,
    isLoading: false,
    error: null,
  });
  return appointment;
}

function renderModal(props?: Partial<Parameters<typeof AppointmentModal>[0]>) {
  return render(
    <AppointmentModal
      appointmentId="appt-001"
      open={true}
      onClose={vi.fn()}
      {...props}
    />,
    { wrapper: createWrapper() }
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe('AppointmentModal — Container and ARIA (Req 1.5, 1.6)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMocks();
  });

  it('renders with role="dialog" and aria-modal="true"', async () => {
    renderModal();

    const dialog = await screen.findByTestId('appointment-modal');
    expect(dialog).toHaveAttribute('role', 'dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
  });

  it('labels the dialog by the job title via aria-labelledby', async () => {
    renderModal();

    const dialog = await screen.findByTestId('appointment-modal');
    expect(dialog).toHaveAttribute('aria-labelledby', 'appointment-modal-title');
  });

  it('places initial focus on the close button when opened (Req 1.5)', async () => {
    renderModal();

    await waitFor(() => {
      const closeBtn = screen.getByRole('button', { name: /close/i });
      expect(document.activeElement).toBe(closeBtn);
    });
  });

  it('calls onClose when Escape is pressed (Req 1.6)', async () => {
    const onClose = vi.fn();
    renderModal({ onClose });

    const modal = await screen.findByTestId('appointment-modal');
    // The onKeyDown handler is on the modal div itself
    modal.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));

    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose when backdrop is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderModal({ onClose });

    await screen.findByTestId('appointment-modal');
    // The backdrop is the first aria-hidden div
    const backdrop = document.querySelector('[aria-hidden="true"]');
    expect(backdrop).toBeTruthy();
    await user.click(backdrop!);

    expect(onClose).toHaveBeenCalled();
  });

  it('does not render when open is false', () => {
    renderModal({ open: false });
    expect(screen.queryByTestId('appointment-modal')).not.toBeInTheDocument();
  });
});

describe('AppointmentModal — Renders all sections', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMocks();
  });

  it('renders the job title as heading', async () => {
    renderModal();

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
        'Spring Startup'
      );
    });
  });

  it('renders the communication timeline section', async () => {
    renderModal();

    await waitFor(() => {
      expect(screen.getByTestId('communication-timeline')).toBeInTheDocument();
    });
  });

  it('renders secondary action buttons (See attached photos, See attached notes, Send Review Request, Edit tags)', async () => {
    renderModal();

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /see attached photos/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /see attached notes/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /send review request/i })
      ).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /edit tags/i })).toBeInTheDocument();
    });
  });

  it('renders the refresh button', async () => {
    renderModal();

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /refresh appointment data/i })
      ).toBeInTheDocument();
    });
  });
});

describe('AppointmentModal — Pending/Draft hide timeline and action track (Req 2.6, 16.2)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it.each(['pending', 'draft'] as AppointmentStatus[])(
    'hides ActionTrack for %s status',
    async (status) => {
      setupMocks({ status });
      renderModal();

      await screen.findByTestId('appointment-modal');

      // ActionTrack renders buttons with labels like "Mark as en route"
      expect(
        screen.queryByRole('button', { name: /mark as en route/i })
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: /mark as on site/i })
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: /mark as done/i })
      ).not.toBeInTheDocument();
    }
  );

  it.each(['pending', 'draft'] as AppointmentStatus[])(
    'hides status badge for %s status',
    async (status) => {
      setupMocks({ status });
      renderModal();

      await screen.findByTestId('appointment-modal');

      // Status badge has aria-label="Status: ..."
      expect(screen.queryByLabelText(/^Status:/)).not.toBeInTheDocument();
    }
  );

  it.each(['confirmed', 'scheduled', 'en_route', 'in_progress'] as AppointmentStatus[])(
    'shows status badge for %s status',
    async (status) => {
      setupMocks({ status });
      renderModal();

      await waitFor(() => {
        expect(screen.getByLabelText(/^Status:/)).toBeInTheDocument();
      });
    }
  );

  it('shows ActionTrack for confirmed status', async () => {
    setupMocks({ status: 'confirmed' });
    renderModal();

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /mark as en route/i })
      ).toBeInTheDocument();
    });
  });
});

describe('AppointmentModal — Terminal states hide footer actions (Req 11.5)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it.each(['completed', 'cancelled', 'no_show'] as AppointmentStatus[])(
    'hides footer Edit/No show/Cancel buttons for %s status',
    async (status) => {
      setupMocks({
        status,
        ...(status === 'completed'
          ? {
              en_route_at: '2025-07-15T09:00:00Z',
              arrived_at: '2025-07-15T09:30:00Z',
              completed_at: '2025-07-15T11:00:00Z',
            }
          : {}),
      });
      renderModal();

      await screen.findByTestId('appointment-modal');

      // Footer buttons should not be present
      expect(screen.queryByRole('button', { name: /^edit$/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /no show/i })).not.toBeInTheDocument();
      // The "Cancel" button in the footer (not the cancel dialog)
      const cancelButtons = screen.queryAllByRole('button', { name: /^cancel$/i });
      // None of them should be the footer cancel button
      const footerCancel = cancelButtons.filter(
        (btn) => btn.closest('[class*="border-t"]') !== null
      );
      expect(footerCancel).toHaveLength(0);
    }
  );

  it.each(['confirmed', 'scheduled', 'en_route', 'in_progress'] as AppointmentStatus[])(
    'shows footer actions for non-terminal %s status',
    async (status) => {
      setupMocks({ status });
      renderModal();

      await waitFor(() => {
        expect(screen.getByText('Edit')).toBeInTheDocument();
        expect(screen.getByText('No show')).toBeInTheDocument();
      });
    }
  );
});

describe('AppointmentModal — Loading and error states', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state while appointment is being fetched', () => {
    mockUseAppointment.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      dataUpdatedAt: 0,
      isFetching: true,
    });
    mockUseAppointmentTimeline.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    renderModal();

    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-label', 'Loading appointment');
  });

  it('shows error state when appointment fetch fails', () => {
    mockUseAppointment.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
      dataUpdatedAt: 0,
      isFetching: false,
    });
    mockUseAppointmentTimeline.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });

    renderModal();

    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-label', 'Error loading appointment');
    expect(screen.getByText('Error loading appointment')).toBeInTheDocument();
  });
});

describe('AppointmentModal — Send Review Request wiring', () => {
  const baseCustomer = {
    id: 'cust-001',
    first_name: 'Jane',
    last_name: 'Smith',
    phone: '612-555-9876' as string | null,
    email: 'jane@example.com',
    properties: [
      {
        is_primary: true,
        property_type: 'Residential',
        address: '123 Elm St',
        city: 'Eden Prairie',
        state: 'MN',
        zip_code: '55344',
        latitude: null,
        longitude: null,
      },
    ],
  };

  async function setCustomerPhone(phone: string | null) {
    const { customerApi } = await import('@/features/customers/api/customerApi');
    vi.mocked(customerApi.get).mockResolvedValue({
      ...baseCustomer,
      phone,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
  }

  beforeEach(async () => {
    vi.clearAllMocks();
    await setCustomerPhone('612-555-9876');
  });

  it('disables the Review button for non-completed status', async () => {
    setupMocks({ status: 'confirmed' });
    renderModal();

    const btn = await screen.findByRole('button', {
      name: /send review request/i,
    });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute(
      'title',
      'Available after appointment is marked completed'
    );
  });

  it('disables the Review button when the customer has no phone', async () => {
    await setCustomerPhone(null);
    setupMocks({
      status: 'completed',
      en_route_at: '2025-07-15T09:00:00Z',
      arrived_at: '2025-07-15T09:30:00Z',
      completed_at: '2025-07-15T11:00:00Z',
    });
    renderModal();

    await waitFor(() => {
      const btn = screen.getByRole('button', {
        name: /send review request/i,
      });
      expect(btn).toBeDisabled();
      expect(btn).toHaveAttribute('title', 'Customer has no phone number');
    });
  });

  it('opens the ReviewConfirmDialog when clicked on a completed appointment with a phone', async () => {
    setupMocks({
      status: 'completed',
      en_route_at: '2025-07-15T09:00:00Z',
      arrived_at: '2025-07-15T09:30:00Z',
      completed_at: '2025-07-15T11:00:00Z',
    });
    const user = userEvent.setup();
    renderModal();

    const btn = await screen.findByRole('button', {
      name: /send review request/i,
    });
    await waitFor(() => expect(btn).not.toBeDisabled());
    await user.click(btn);

    await waitFor(() => {
      expect(screen.getByTestId('review-confirm-dialog')).toBeInTheDocument();
    });
    const dialog = screen.getByTestId('review-confirm-dialog');
    expect(dialog).toHaveAttribute('data-customer-name', 'Jane Smith');
    expect(dialog).toHaveAttribute('data-customer-phone', '612-555-9876');
  });
});

describe('AppointmentModal — Draft-specific behavior', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders SendConfirmationButton for draft appointments', async () => {
    setupMocks({ status: 'draft' });
    renderModal();

    await waitFor(() => {
      expect(screen.getByTestId('send-confirmation-btn')).toBeInTheDocument();
    });
  });

  it('does not render SendConfirmationButton for non-draft appointments', async () => {
    setupMocks({ status: 'confirmed' });
    renderModal();

    await screen.findByTestId('appointment-modal');
    expect(screen.queryByTestId('send-confirmation-btn')).not.toBeInTheDocument();
  });
});
