/**
 * DayMode tests — hour ruler, lane positioning, drag-drop reschedule
 * (same row), drag-drop reassign (cross row), past-8pm rejection,
 * NowLine presence, loading/empty states.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { Appointment, DailyScheduleResponse } from '../../types';
import type { Staff } from '@/features/staff/types';

const mockUseDailySchedule = vi.fn();
const mockUseStaff = vi.fn();
const mockUseUtilizationReport = vi.fn();
const mockMutateAsync = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

vi.mock('../../hooks/useAppointments', () => ({
  useDailySchedule: (...args: unknown[]) => mockUseDailySchedule(...args),
}));
vi.mock('@/features/staff/hooks/useStaff', () => ({
  useStaff: (...args: unknown[]) => mockUseStaff(...args),
}));
vi.mock('../../hooks/useAIScheduling', () => ({
  useUtilizationReport: (...args: unknown[]) =>
    mockUseUtilizationReport(...args),
}));
vi.mock('../../hooks/useAppointmentMutations', () => ({
  useUpdateAppointment: () => ({ mutateAsync: mockMutateAsync }),
}));
vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    error: (...args: unknown[]) => mockToastError(...args),
  },
}));
vi.mock('../SendConfirmationButton', () => ({
  SendConfirmationButton: () => <div data-testid="send-confirmation-button" />,
}));

import { DayMode } from './DayMode';

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

const baseAppt: Omit<Appointment, 'id' | 'time_window_start' | 'time_window_end'> = {
  job_id: 'job-1',
  staff_id: 'staff-1',
  scheduled_date: '2025-06-15',
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

function buildDaily(
  appointments: Appointment[]
): DailyScheduleResponse {
  return {
    date: TARGET_DATE_STR,
    appointments,
    total_count: appointments.length,
  };
}

/**
 * Fire a drop event with a controlled clientX. `clientX` is a read-only
 * getter on MouseEvent in jsdom, so we override it via defineProperty
 * after creating the synthetic event — plain assignment silently no-ops.
 */
function fireDropAt(
  target: HTMLElement,
  clientX: number,
  payload: string
): void {
  const event = new Event('drop', { bubbles: true, cancelable: true });
  Object.defineProperty(event, 'clientX', { value: clientX });
  Object.defineProperty(event, 'clientY', { value: 40 });
  Object.defineProperty(event, 'dataTransfer', {
    value: { getData: () => payload, setData: () => {}, effectAllowed: '', dropEffect: '' },
  });
  target.dispatchEvent(event);
}

// Pick a fixed past date so NowLine never renders by default. Tests that
// need NowLine override the date (and system time) explicitly.
const TARGET_DATE = new Date(2025, 5, 15); // 2025-06-15
const TARGET_DATE_STR = '2025-06-15';

describe('DayMode', () => {
  beforeEach(() => {
    mockUseDailySchedule.mockReturnValue({
      data: buildDaily([
        {
          ...baseAppt,
          id: 'appt-1',
          time_window_start: '08:00:00',
          time_window_end: '09:30:00',
        },
        {
          ...baseAppt,
          id: 'appt-2',
          time_window_start: '13:00:00',
          time_window_end: '14:00:00',
        },
      ]),
      isLoading: false,
      isError: false,
    });
    mockUseStaff.mockReturnValue({
      data: { items: mockStaff, total: 2, page: 1, page_size: 100, total_pages: 1 },
      isLoading: false,
      isError: false,
    });
    mockUseUtilizationReport.mockReturnValue({
      data: {
        schedule_date: TARGET_DATE_STR,
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
      },
      isLoading: false,
      isError: false,
    });
    mockMutateAsync.mockReset();
    mockToastSuccess.mockReset();
    mockToastError.mockReset();
  });

  it('renders the day mode root with hour ticks at 6am, 8am, 8pm', () => {
    render(
      <DayMode
        date={TARGET_DATE}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
      />,
      { wrapper }
    );
    expect(screen.getByTestId('schedule-day-mode')).toBeInTheDocument();
    // 6am tick (360), 8am tick (480), 8pm tick (1200)
    expect(screen.getAllByTestId('hour-tick-360').length).toBeGreaterThan(0);
    expect(screen.getAllByTestId('hour-tick-480').length).toBeGreaterThan(0);
    expect(screen.getAllByTestId('hour-tick-1200').length).toBeGreaterThan(0);
  });

  it('renders a tech header for each active tech', () => {
    render(
      <DayMode
        date={TARGET_DATE}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
      />,
      { wrapper }
    );
    expect(screen.getByTestId('tech-header-staff-1')).toBeInTheDocument();
    expect(screen.getByTestId('tech-header-staff-2')).toBeInTheDocument();
  });

  it('positions an appointment card with correct left % and width %', () => {
    render(
      <DayMode
        date={TARGET_DATE}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
      />,
      { wrapper }
    );
    const card = screen.getByTestId('appt-card-appt-1') as HTMLDivElement;
    // 8:00am (480 min) → (480-360)/840 = 14.2857%
    // duration 90min → 90/840 = 10.7142%
    expect(card.style.left).toMatch(/^14\./);
    expect(card.style.width).toMatch(/^10\./);
    // top: lane 0 → 2px; height fixed at 36px
    expect(card.style.top).toBe('2px');
    expect(card.style.height).toBe('36px');
  });

  it('places overlapping appointments in different lanes', () => {
    mockUseDailySchedule.mockReturnValue({
      data: buildDaily([
        {
          ...baseAppt,
          id: 'appt-overlap-1',
          time_window_start: '08:00:00',
          time_window_end: '10:00:00',
        },
        {
          ...baseAppt,
          id: 'appt-overlap-2',
          time_window_start: '09:00:00',
          time_window_end: '11:00:00',
        },
      ]),
      isLoading: false,
      isError: false,
    });
    render(
      <DayMode
        date={TARGET_DATE}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
      />,
      { wrapper }
    );
    const c1 = screen.getByTestId('appt-card-appt-overlap-1') as HTMLDivElement;
    const c2 = screen.getByTestId('appt-card-appt-overlap-2') as HTMLDivElement;
    expect(c1.style.top).toBe('2px'); // lane 0
    expect(c2.style.top).toBe('40px'); // lane 1 → 1*38 + 2
  });

  it('does NOT render NowLine when date is not today', () => {
    render(
      <DayMode
        date={TARGET_DATE}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
      />,
      { wrapper }
    );
    expect(screen.queryByTestId('now-line')).not.toBeInTheDocument();
  });

  it('renders NowLine when date is today and now is within 6am-8pm', () => {
    // Use a fixed "now" inside the visible window via system time mock.
    // Mock to 10:30am today, then set the date prop to today.
    const fakeNow = new Date();
    fakeNow.setHours(10, 30, 0, 0);
    vi.useFakeTimers();
    vi.setSystemTime(fakeNow);

    render(
      <DayMode
        date={fakeNow}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
      />,
      { wrapper }
    );
    // NowLine renders once per tech row (we have 2 active techs).
    expect(screen.getAllByTestId('now-line').length).toBeGreaterThan(0);
    vi.useRealTimers();
  });

  it('fires reschedule (same staff) PATCH on drop within the same row', async () => {
    mockMutateAsync.mockResolvedValueOnce({});
    render(
      <DayMode
        date={TARGET_DATE}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
      />,
      { wrapper }
    );
    const targetCell = screen.getByTestId(`cell-staff-1-${TARGET_DATE_STR}`);
    // Stub bounding rect: 1000px wide. clientX=0 → 6am. We want to land at ~10am.
    // 10am = 600min; (600-360)/840 = 28.5714%; clientX = 0.2857*1000 = 285.7
    targetCell.getBoundingClientRect = () =>
      ({ left: 0, top: 0, width: 1000, height: 80, right: 1000, bottom: 80, x: 0, y: 0, toJSON: () => ({}) } as DOMRect);

    const payload = JSON.stringify({
      appointmentId: 'appt-1',
      originStaffId: 'staff-1',
      originDate: TARGET_DATE_STR,
      originStartTime: '08:00:00',
      originEndTime: '09:30:00',
    });
    fireEvent.dragOver(targetCell, { dataTransfer: { dropEffect: '' } });
    fireDropAt(targetCell, 286, payload);
    await Promise.resolve();
    expect(mockMutateAsync).toHaveBeenCalledTimes(1);
    const call = mockMutateAsync.mock.calls[0]?.[0] as {
      id: string;
      data: {
        staff_id: string;
        scheduled_date: string;
        time_window_start: string;
        time_window_end: string;
      };
    };
    expect(call.id).toBe('appt-1');
    expect(call.data.staff_id).toBe('staff-1');
    expect(call.data.scheduled_date).toBe(TARGET_DATE_STR);
    // ~10am snapped to 15min: 10:00:00 (rawMin=600) — duration preserved (90min) → 11:30:00
    expect(call.data.time_window_start).toBe('10:00:00');
    expect(call.data.time_window_end).toBe('11:30:00');
    expect(mockToastSuccess).toHaveBeenCalledWith('Rescheduled');
  });

  it('fires reassign+reschedule PATCH on drop into a different tech row', async () => {
    mockMutateAsync.mockResolvedValueOnce({});
    render(
      <DayMode
        date={TARGET_DATE}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
      />,
      { wrapper }
    );
    const targetCell = screen.getByTestId(`cell-staff-2-${TARGET_DATE_STR}`);
    targetCell.getBoundingClientRect = () =>
      ({ left: 0, top: 0, width: 1000, height: 80, right: 1000, bottom: 80, x: 0, y: 0, toJSON: () => ({}) } as DOMRect);

    const payload = JSON.stringify({
      appointmentId: 'appt-1',
      originStaffId: 'staff-1',
      originDate: TARGET_DATE_STR,
      originStartTime: '08:00:00',
      originEndTime: '09:30:00',
    });
    fireDropAt(targetCell, 286, payload);
    await Promise.resolve();
    expect(mockMutateAsync).toHaveBeenCalledTimes(1);
    const call = mockMutateAsync.mock.calls[0]?.[0] as {
      data: { staff_id: string };
    };
    expect(call.data.staff_id).toBe('staff-2');
    expect(mockToastSuccess).toHaveBeenCalledWith('Reassigned and rescheduled');
  });

  it('rejects drops past 8pm with a toast and no mutation', async () => {
    render(
      <DayMode
        date={TARGET_DATE}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
      />,
      { wrapper }
    );
    const targetCell = screen.getByTestId(`cell-staff-1-${TARGET_DATE_STR}`);
    targetCell.getBoundingClientRect = () =>
      ({ left: 0, top: 0, width: 1000, height: 80, right: 1000, bottom: 80, x: 0, y: 0, toJSON: () => ({}) } as DOMRect);

    // Drop at the far right (≈ 8pm) with a 3-hour duration → would end past 8pm.
    const payload = JSON.stringify({
      appointmentId: 'appt-long',
      originStaffId: 'staff-1',
      originDate: TARGET_DATE_STR,
      originStartTime: '08:00:00',
      originEndTime: '11:00:00', // 3-hour duration
    });
    fireDropAt(targetCell, 1000, payload); // far right → ~8pm
    await Promise.resolve();
    expect(mockMutateAsync).not.toHaveBeenCalled();
    expect(mockToastError).toHaveBeenCalledWith(
      'Cannot schedule past 8pm — pick an earlier slot'
    );
  });

  it('renders the loading spinner while data is loading', () => {
    mockUseDailySchedule.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });
    render(
      <DayMode
        date={TARGET_DATE}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
      />,
      { wrapper }
    );
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('renders the empty state when there are no active techs', () => {
    mockUseStaff.mockReturnValue({
      data: { items: [], total: 0, page: 1, page_size: 100, total_pages: 0 },
      isLoading: false,
      isError: false,
    });
    render(
      <DayMode
        date={TARGET_DATE}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
      />,
      { wrapper }
    );
    expect(screen.getByTestId('schedule-empty-state')).toBeInTheDocument();
  });

  it('renders the error state when the schedule fetch fails', () => {
    mockUseDailySchedule.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });
    render(
      <DayMode
        date={TARGET_DATE}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
      />,
      { wrapper }
    );
    expect(screen.getByText('Failed to load schedule.')).toBeInTheDocument();
  });

  it('fires onEmptyCellClick when an empty tech row + button is clicked', () => {
    const onEmpty = vi.fn();
    render(
      <DayMode
        date={TARGET_DATE}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={onEmpty}
      />,
      { wrapper }
    );
    // staff-2 has zero appointments — its strip hosts the + button.
    const cell = screen.getByTestId(`cell-staff-2-${TARGET_DATE_STR}`);
    const plusBtn = cell.querySelector('button');
    expect(plusBtn).not.toBeNull();
    fireEvent.click(plusBtn!);
    expect(onEmpty).toHaveBeenCalledWith('staff-2', TARGET_DATE_STR);
  });
});
