/**
 * Tests for SendDayConfirmationsButton component (H-2).
 *
 * Verifies defensive DRAFT re-filter: the component only renders when at
 * least one DRAFT appointment is passed, and it only submits DRAFT ids even
 * when the caller passes a mixed list.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { SendDayConfirmationsButton } from './SendDayConfirmationsButton';
import type { Appointment } from '../types';

// Mock the bulk send mutation hook
const mockBulkSendMutate = vi.fn();

vi.mock('../hooks/useAppointmentMutations', () => ({
  useBulkSendConfirmations: () => ({
    mutateAsync: mockBulkSendMutate,
    isPending: false,
  }),
}));

// Mock sonner toasts
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

describe('SendDayConfirmationsButton (H-2)', () => {
  beforeEach(() => {
    mockBulkSendMutate.mockReset();
    mockBulkSendMutate.mockResolvedValue({
      sent_count: 0,
      deferred_count: 0,
      skipped_count: 0,
      failed_count: 0,
    });
  });

  it('renders only when there is at least one DRAFT', () => {
    // Empty drafts → render nothing.
    const { container: emptyContainer } = render(
      <SendDayConfirmationsButton date="2026-04-20" draftAppointments={[]} />,
      { wrapper: createWrapper() },
    );
    expect(emptyContainer.firstChild).toBeNull();

    // All non-DRAFT appointments → render nothing.
    const allNonDraft = [
      makeAppointment('a', 'scheduled'),
      makeAppointment('b', 'confirmed'),
    ];
    const { container: nonDraftContainer } = render(
      <SendDayConfirmationsButton
        date="2026-04-20"
        draftAppointments={allNonDraft}
      />,
      { wrapper: createWrapper() },
    );
    expect(nonDraftContainer.firstChild).toBeNull();
  });

  it('renders with count badge equal to DRAFT-only subset', () => {
    const mixed = [
      makeAppointment('a', 'draft'),
      makeAppointment('b', 'scheduled'),
      makeAppointment('c', 'draft'),
      makeAppointment('d', 'confirmed'),
    ];
    render(
      <SendDayConfirmationsButton
        date="2026-04-20"
        draftAppointments={mixed}
      />,
      { wrapper: createWrapper() },
    );
    const btn = screen.getByTestId('send-day-confirmations-2026-04-20');
    // Only 2 DRAFTs in the mix.
    expect(btn).toHaveTextContent('2');
  });

  it('submits only draft ids on click', async () => {
    const mixed = [
      makeAppointment('draft-a', 'draft'),
      makeAppointment('sched-1', 'scheduled'),
      makeAppointment('draft-b', 'draft'),
      makeAppointment('conf-1', 'confirmed'),
    ];
    render(
      <SendDayConfirmationsButton
        date="2026-04-20"
        draftAppointments={mixed}
      />,
      { wrapper: createWrapper() },
    );
    fireEvent.click(screen.getByTestId('send-day-confirmations-2026-04-20'));

    await waitFor(() => {
      expect(mockBulkSendMutate).toHaveBeenCalledTimes(1);
    });
    expect(mockBulkSendMutate).toHaveBeenCalledWith({
      appointment_ids: ['draft-a', 'draft-b'],
      date_from: '2026-04-20',
      date_to: '2026-04-20',
    });
  });
});
