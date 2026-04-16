/**
 * Tests for SendAllConfirmationsButton component (H-2).
 *
 * Verifies defensive DRAFT re-filter: even when callers accidentally pass
 * mixed-status appointments, the count badge, modal list, and submit payload
 * only include DRAFT appointments.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { SendAllConfirmationsButton } from './SendAllConfirmationsButton';
import type { Appointment } from '../types';

// Mock the bulk send mutation hook
const mockBulkSendMutate = vi.fn();

vi.mock('../hooks/useAppointmentMutations', () => ({
  useBulkSendConfirmations: () => ({
    mutateAsync: mockBulkSendMutate,
    isPending: false,
  }),
}));

// Mock sonner toasts (they're called but don't need real render)
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn(),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

/**
 * Build a minimal Appointment object for tests.
 */
const makeAppointment = (
  id: string,
  status: Appointment['status'],
  overrides: Partial<Appointment> = {},
): Appointment => ({
  id,
  job_id: `job-${id}`,
  staff_id: 'staff-1',
  scheduled_date: '2026-04-20',
  time_window_start: '09:00:00',
  time_window_end: '11:00:00',
  status,
  arrived_at: null,
  en_route_at: null,
  completed_at: null,
  notes: null,
  route_order: null,
  estimated_arrival: null,
  created_at: '2026-04-16T00:00:00Z',
  updated_at: '2026-04-16T00:00:00Z',
  job_type: 'Spring Startup',
  customer_name: `Customer ${id}`,
  staff_name: 'Tech A',
  service_agreement_id: null,
  ...overrides,
});

describe('SendAllConfirmationsButton (H-2)', () => {
  beforeEach(() => {
    mockBulkSendMutate.mockReset();
    mockBulkSendMutate.mockResolvedValue({
      sent_count: 0,
      deferred_count: 0,
      skipped_count: 0,
      failed_count: 0,
    });
  });

  it('renders correct count when all appointments are drafts', () => {
    const drafts = [
      makeAppointment('a', 'draft'),
      makeAppointment('b', 'draft'),
      makeAppointment('c', 'draft'),
    ];
    render(<SendAllConfirmationsButton draftAppointments={drafts} />, {
      wrapper: createWrapper(),
    });
    const badge = screen.getByTestId('send-all-confirmations-btn');
    expect(badge).toHaveTextContent('3');
  });

  it('renders correct count when caller accidentally mixes in scheduled appointments', () => {
    // Caller regresses and passes scheduled + confirmed + draft.
    const mixed = [
      makeAppointment('a', 'draft'),
      makeAppointment('b', 'scheduled'),
      makeAppointment('c', 'confirmed'),
      makeAppointment('d', 'draft'),
      makeAppointment('e', 'completed'),
    ];
    render(<SendAllConfirmationsButton draftAppointments={mixed} />, {
      wrapper: createWrapper(),
    });
    const badge = screen.getByTestId('send-all-confirmations-btn');
    // Should show 2 (only the drafts), NOT 5.
    expect(badge).toHaveTextContent('2');
    expect(badge).not.toHaveTextContent('5');
  });

  it('renders nothing when no drafts remain after filter', () => {
    const noneDrafts = [
      makeAppointment('a', 'scheduled'),
      makeAppointment('b', 'confirmed'),
    ];
    const { container } = render(
      <SendAllConfirmationsButton draftAppointments={noneDrafts} />,
      { wrapper: createWrapper() },
    );
    expect(container.firstChild).toBeNull();
  });

  it('submits only draft ids when caller passes mixed list', async () => {
    const mixed = [
      makeAppointment('draft-1', 'draft'),
      makeAppointment('sched-1', 'scheduled'),
      makeAppointment('conf-1', 'confirmed'),
      makeAppointment('draft-2', 'draft'),
    ];
    render(<SendAllConfirmationsButton draftAppointments={mixed} />, {
      wrapper: createWrapper(),
    });

    // Open modal
    fireEvent.click(screen.getByTestId('send-all-confirmations-btn'));

    // Modal list should only show DRAFT customers
    expect(screen.getByText('Customer draft-1')).toBeInTheDocument();
    expect(screen.getByText('Customer draft-2')).toBeInTheDocument();
    expect(screen.queryByText('Customer sched-1')).not.toBeInTheDocument();
    expect(screen.queryByText('Customer conf-1')).not.toBeInTheDocument();

    // Confirm send
    fireEvent.click(screen.getByTestId('send-all-confirm-btn'));

    await waitFor(() => {
      expect(mockBulkSendMutate).toHaveBeenCalledTimes(1);
    });
    // Submitted ids should be DRAFT-only.
    expect(mockBulkSendMutate).toHaveBeenCalledWith({
      appointment_ids: ['draft-1', 'draft-2'],
    });
  });
});
