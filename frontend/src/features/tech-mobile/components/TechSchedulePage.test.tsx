import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import type { Appointment, AppointmentStatus } from '@/features/schedule/types';

// Mock the AppointmentModal so it doesn't pull its full tree into the test.
const mockModal = vi.fn(() => null);
vi.mock('@/features/schedule/components/AppointmentModal', () => ({
  AppointmentModal: (props: { appointmentId: string; open: boolean }) =>
    mockModal(props) as ReactNode,
}));

const mockUseAuth = vi.fn();
vi.mock('@/features/auth/components/AuthProvider', () => ({
  useAuth: () => mockUseAuth(),
}));

const mockUseStaffDailySchedule = vi.fn();
vi.mock('@/features/schedule/hooks/useAppointments', () => ({
  useStaffDailySchedule: (...args: unknown[]) =>
    mockUseStaffDailySchedule(...args),
}));

import { TechSchedulePage } from './TechSchedulePage';

function makeAppointment(overrides: Partial<Appointment> = {}): Appointment {
  return {
    id: 'a1',
    job_id: 'j1',
    staff_id: 'staff-1',
    scheduled_date: '2026-05-01',
    time_window_start: '09:00:00',
    time_window_end: '10:00:00',
    status: 'scheduled' as AppointmentStatus,
    arrived_at: null,
    en_route_at: null,
    completed_at: null,
    notes: null,
    route_order: null,
    estimated_arrival: null,
    created_at: '2026-04-30T00:00:00Z',
    updated_at: '2026-04-30T00:00:00Z',
    job_type: 'Spring',
    customer_name: 'Alpha',
    staff_name: 'Vas',
    service_agreement_id: null,
    priority_level: null,
    property_summary: null,
    ...overrides,
  };
}

function wrap(node: ReactNode): ReactNode {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <MemoryRouter>
      <QueryClientProvider client={client}>{node}</QueryClientProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  mockModal.mockClear();
  mockUseAuth.mockReturnValue({
    user: { id: 'staff-1', name: 'Vas Grin', role: 'tech' },
  });
});

describe('TechSchedulePage', () => {
  it('renders 3 skeleton cards while loading', () => {
    mockUseStaffDailySchedule.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    });
    const { container } = render(wrap(<TechSchedulePage />));
    expect(container.querySelectorAll('.animate-pulse')).toHaveLength(3);
  });

  it('renders empty state when no appointments', () => {
    mockUseStaffDailySchedule.mockReturnValue({
      data: { appointments: [] },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
    render(wrap(<TechSchedulePage />));
    expect(screen.getByText('No appointments today')).toBeInTheDocument();
  });

  it('renders one card per visible appointment, excluding cancelled/no_show', () => {
    mockUseStaffDailySchedule.mockReturnValue({
      data: {
        appointments: [
          makeAppointment({ id: 'a1', customer_name: 'Alpha' }),
          makeAppointment({
            id: 'a2',
            customer_name: 'Beta',
            status: 'cancelled',
          }),
          makeAppointment({
            id: 'a3',
            customer_name: 'Gamma',
            status: 'no_show',
          }),
          makeAppointment({
            id: 'a4',
            customer_name: 'Delta',
            status: 'completed',
          }),
        ],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
    render(wrap(<TechSchedulePage />));
    expect(screen.getByText('Alpha')).toBeInTheDocument();
    expect(screen.getByText('Delta')).toBeInTheDocument();
    expect(screen.queryByText('Beta')).not.toBeInTheDocument();
    expect(screen.queryByText('Gamma')).not.toBeInTheDocument();
  });

  it('opens AppointmentModal when a card is clicked', async () => {
    const user = userEvent.setup();
    mockUseStaffDailySchedule.mockReturnValue({
      data: {
        appointments: [makeAppointment({ id: 'pick-me' })],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
    render(wrap(<TechSchedulePage />));

    const card = screen.getByTestId('mobile-job-card-upcoming');
    await user.click(card);

    expect(mockModal).toHaveBeenCalledWith(
      expect.objectContaining({ appointmentId: 'pick-me', open: true })
    );
  });

  it('renders an error card when isError is true', () => {
    mockUseStaffDailySchedule.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: vi.fn(),
    });
    render(wrap(<TechSchedulePage />));
    expect(
      screen.getByText("Couldn't load your schedule")
    ).toBeInTheDocument();
  });
});
