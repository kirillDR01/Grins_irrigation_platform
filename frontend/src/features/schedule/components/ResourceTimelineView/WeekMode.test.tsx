/**
 * WeekMode tests — render, sparkline, capacity-color thresholds,
 * empty-state, and day-header drill-in.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { Appointment, WeeklyScheduleResponse } from '../../types';
import type { Staff } from '@/features/staff/types';

const mockUseWeeklySchedule = vi.fn();
const mockUseStaff = vi.fn();
const mockUseWeeklyUtilization = vi.fn();
const mockUseWeeklyCapacity = vi.fn();
const mockMutateAsync = vi.fn();

vi.mock('../../hooks/useAppointments', () => ({
  useWeeklySchedule: (...args: unknown[]) => mockUseWeeklySchedule(...args),
}));
vi.mock('@/features/staff/hooks/useStaff', () => ({
  useStaff: (...args: unknown[]) => mockUseStaff(...args),
}));
vi.mock('../../hooks/useWeeklyUtilization', () => ({
  useWeeklyUtilization: (...args: unknown[]) =>
    mockUseWeeklyUtilization(...args),
}));
vi.mock('../../hooks/useWeeklyCapacity', () => ({
  useWeeklyCapacity: (...args: unknown[]) => mockUseWeeklyCapacity(...args),
}));
vi.mock('../../hooks/useAppointmentMutations', () => ({
  useUpdateAppointment: () => ({ mutateAsync: mockMutateAsync }),
}));
vi.mock('../SendDayConfirmationsButton', () => ({
  SendDayConfirmationsButton: () => (
    <div data-testid="send-day-confirmations-button" />
  ),
}));
vi.mock('../SendConfirmationButton', () => ({
  SendConfirmationButton: () => <div data-testid="send-confirmation-button" />,
}));

import { WeekMode } from './WeekMode';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const mockStaff: Staff[] = [
  {
    id: 'staff-1',
    name: 'Mike Davis',
    phone: '+15555550001',
    email: null,
    role: 'tech',
    skill_level: 'senior',
    certifications: null,
    is_available: true,
    availability_notes: null,
    hourly_rate: null,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'staff-2',
    name: 'Sarah Kim',
    phone: '+15555550002',
    email: null,
    role: 'tech',
    skill_level: 'junior',
    certifications: null,
    is_available: true,
    availability_notes: null,
    hourly_rate: null,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

const baseAppt: Omit<Appointment, 'id' | 'staff_id' | 'scheduled_date'> = {
  job_id: 'job-1',
  time_window_start: '08:00:00',
  time_window_end: '09:30:00',
  status: 'confirmed',
  arrived_at: null,
  en_route_at: null,
  completed_at: null,
  notes: null,
  route_order: null,
  estimated_arrival: null,
  created_at: '2026-04-29T00:00:00Z',
  updated_at: '2026-04-29T00:00:00Z',
  job_type: 'Spring opening',
  customer_name: 'Henderson',
  staff_name: 'Mike Davis',
  service_agreement_id: null,
  priority_level: null,
  reply_state: null,
};

function buildWeekly(): WeeklyScheduleResponse {
  return {
    start_date: '2026-04-27',
    end_date: '2026-05-04',
    days: [
      {
        date: '2026-04-27',
        appointments: [
          {
            ...baseAppt,
            id: 'appt-1',
            staff_id: 'staff-1',
            scheduled_date: '2026-04-27',
          },
          {
            ...baseAppt,
            id: 'appt-2',
            staff_id: 'staff-1',
            scheduled_date: '2026-04-27',
            time_window_start: '13:00:00',
            time_window_end: '14:00:00',
          },
        ],
        total_count: 2,
      },
      ...Array.from({ length: 6 }, (_, i) => ({
        date: `2026-04-${(28 + i).toString().padStart(2, '0')}`,
        appointments: [],
        total_count: 0,
      })),
    ],
    total_appointments: 2,
  };
}

describe('WeekMode', () => {
  beforeEach(() => {
    mockUseWeeklySchedule.mockReturnValue({
      data: buildWeekly(),
      isLoading: false,
      isError: false,
    });
    mockUseStaff.mockReturnValue({
      data: { items: mockStaff, total: 2, page: 1, page_size: 100, total_pages: 1 },
      isLoading: false,
      isError: false,
    });
    mockUseWeeklyUtilization.mockReturnValue({
      days: Array.from({ length: 7 }, () => ({
        schedule_date: '2026-04-27',
        resources: [
          {
            staff_id: 'staff-1',
            name: 'Mike Davis',
            total_minutes: 480,
            assigned_minutes: 240,
            drive_minutes: 0,
            utilization_pct: 50,
          },
        ],
      })),
      isLoading: false,
      isError: false,
    });
    mockUseWeeklyCapacity.mockReturnValue({
      days: [
        // First day → 90% (orange)
        { utilization_pct: 90 },
        // Second day → 50% (teal)
        { utilization_pct: 50 },
        ...Array.from({ length: 5 }, () => ({ utilization_pct: 60 })),
      ],
      isLoading: false,
      isError: false,
    });
    mockMutateAsync.mockReset();
  });

  it('renders the week mode root and one row per active tech', () => {
    render(
      <WeekMode
        weekStart={new Date(2026, 3, 27)}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
        onDayHeaderClick={vi.fn()}
      />,
      { wrapper }
    );
    expect(screen.getByTestId('schedule-week-mode')).toBeInTheDocument();
    expect(screen.getByTestId('tech-header-staff-1')).toBeInTheDocument();
    expect(screen.getByTestId('tech-header-staff-2')).toBeInTheDocument();
  });

  it('renders day headers for all 7 dates', () => {
    render(
      <WeekMode
        weekStart={new Date(2026, 3, 27)}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
        onDayHeaderClick={vi.fn()}
      />,
      { wrapper }
    );
    expect(screen.getByTestId('day-header-2026-04-27')).toBeInTheDocument();
    expect(screen.getByTestId('day-header-2026-05-03')).toBeInTheDocument();
  });

  it('drills into day mode when a day header is clicked', () => {
    const onDrillIn = vi.fn();
    render(
      <WeekMode
        weekStart={new Date(2026, 3, 27)}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
        onDayHeaderClick={onDrillIn}
      />,
      { wrapper }
    );
    const header = screen.getByTestId('day-header-2026-04-27');
    fireEvent.click(header.querySelector('button')!);
    expect(onDrillIn).toHaveBeenCalledWith('2026-04-27');
  });

  it('renders sparkline rects for each non-cancelled appointment', () => {
    render(
      <WeekMode
        weekStart={new Date(2026, 3, 27)}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
        onDayHeaderClick={vi.fn()}
      />,
      { wrapper }
    );
    const sparkline = screen.getByTestId('sparkline-staff-1-2026-04-27');
    expect(sparkline.tagName.toLowerCase()).toBe('svg');
    expect(sparkline.querySelectorAll('rect').length).toBe(2);
  });

  it('paints capacity bar orange when utilization >= 85, teal otherwise', () => {
    render(
      <WeekMode
        weekStart={new Date(2026, 3, 27)}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
        onDayHeaderClick={vi.fn()}
      />,
      { wrapper }
    );
    const orangeCell = screen.getByTestId('capacity-2026-04-27');
    expect(orangeCell.innerHTML).toContain('bg-orange-500');
    const tealCell = screen.getByTestId('capacity-2026-04-28');
    expect(tealCell.innerHTML).toContain('bg-teal-500');
  });

  it('fires onEmptyCellClick when a placeholder + button is clicked', () => {
    const onEmpty = vi.fn();
    render(
      <WeekMode
        weekStart={new Date(2026, 3, 27)}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={onEmpty}
        onDayHeaderClick={vi.fn()}
      />,
      { wrapper }
    );
    // staff-2 has zero appointments — its row's first cell hosts the + button
    const cell = screen.getByTestId('cell-staff-2-2026-04-27');
    const plusBtn = cell.querySelector('button')!;
    fireEvent.click(plusBtn);
    expect(onEmpty).toHaveBeenCalledWith('staff-2', '2026-04-27');
  });

  it('renders empty state when there are no active techs', () => {
    mockUseStaff.mockReturnValue({
      data: { items: [], total: 0, page: 1, page_size: 100, total_pages: 0 },
      isLoading: false,
      isError: false,
    });
    render(
      <WeekMode
        weekStart={new Date(2026, 3, 27)}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
        onDayHeaderClick={vi.fn()}
      />,
      { wrapper }
    );
    expect(screen.getByTestId('schedule-empty-state')).toBeInTheDocument();
  });

  it('renders the loading spinner while data is loading', () => {
    mockUseWeeklySchedule.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });
    render(
      <WeekMode
        weekStart={new Date(2026, 3, 27)}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
        onDayHeaderClick={vi.fn()}
      />,
      { wrapper }
    );
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('renders 0% utilized — not Loading… — when utilization settles empty', () => {
    mockUseWeeklyUtilization.mockReturnValue({
      days: Array.from({ length: 7 }, () => ({
        schedule_date: '2026-04-27',
        resources: [],
      })),
      isLoading: false,
      isError: false,
    });

    render(
      <WeekMode
        weekStart={new Date(2026, 3, 27)}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
        onDayHeaderClick={vi.fn()}
      />,
      { wrapper }
    );

    const header = screen.getByTestId('tech-header-staff-1');
    expect(header.textContent).toContain('0% utilized');
    expect(header.textContent).not.toContain('Loading');
  });

  it('renders Loading… while utilization is genuinely loading', () => {
    mockUseWeeklyUtilization.mockReturnValue({
      days: Array.from({ length: 7 }, () => undefined),
      isLoading: true,
      isError: false,
    });
    render(
      <WeekMode
        weekStart={new Date(2026, 3, 27)}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
        onDayHeaderClick={vi.fn()}
      />,
      { wrapper }
    );
    const header = screen.getByTestId('tech-header-staff-1');
    expect(header.textContent).toContain('Loading');
  });

  it('triggers updateAppointment mutation when an appointment is dropped on a different cell', async () => {
    mockMutateAsync.mockResolvedValueOnce({});
    render(
      <WeekMode
        weekStart={new Date(2026, 3, 27)}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
        onDayHeaderClick={vi.fn()}
      />,
      { wrapper }
    );
    const targetCell = screen.getByTestId('cell-staff-2-2026-04-28');
    const payload = JSON.stringify({
      appointmentId: 'appt-1',
      originStaffId: 'staff-1',
      originDate: '2026-04-27',
      originStartTime: '08:00:00',
      originEndTime: '09:30:00',
    });
    fireEvent.dragOver(targetCell, {
      dataTransfer: { dropEffect: '' },
    });
    fireEvent.drop(targetCell, {
      dataTransfer: { getData: () => payload },
    });
    // Allow mutateAsync microtask to settle
    await Promise.resolve();
    expect(mockMutateAsync).toHaveBeenCalledWith({
      id: 'appt-1',
      data: {
        staff_id: 'staff-2',
        scheduled_date: '2026-04-28',
      },
    });
  });
});
