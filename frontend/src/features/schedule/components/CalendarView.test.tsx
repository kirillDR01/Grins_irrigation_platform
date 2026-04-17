/**
 * Tests for CalendarView week-start alignment (Finding H-3).
 *
 * The schedule feature must use Monday-based weeks (weekStartsOn: 1) to match
 * the Jobs-tab Week Picker and the backend align_to_week(). A regression to
 * Sunday-based weeks causes week-boundary jobs to land in the wrong week.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { CalendarView } from './CalendarView';

// ── Mock hooks ───────────────────────────────────────────────────────────────

const mockUseWeeklySchedule = vi.fn();

vi.mock('../hooks/useAppointments', () => ({
  useWeeklySchedule: (startDate?: string, endDate?: string) =>
    mockUseWeeklySchedule(startDate, endDate),
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
  useUpdateAppointment: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

vi.mock('@/features/staff/hooks/useStaff', () => ({
  useStaff: () => ({
    data: { items: [], total: 0 },
    isLoading: false,
  }),
}));

// Mock sub-components that depend on query context we don't care about here.
vi.mock('./SendConfirmationButton', () => ({
  SendConfirmationButton: () => <div data-testid="send-confirmation-button" />,
}));
vi.mock('./SendDayConfirmationsButton', () => ({
  SendDayConfirmationsButton: () => (
    <div data-testid="send-day-confirmations-button" />
  ),
}));

// ── Mock FullCalendar ────────────────────────────────────────────────────────
//
// FullCalendar renders a live DOM calendar that is awkward to assert against
// in jsdom, so we swap it out for a stub that exposes its configuration props
// (firstDay) and lets the test fire the `datesSet` callback with a controlled
// argument. This verifies the integration without depending on FullCalendar's
// internal rendering.

type StubFullCalendarProps = {
  firstDay?: number;
  datesSet?: (arg: { start: Date; end: Date; startStr: string; endStr: string; timeZone: string; view: unknown }) => void;
};

vi.mock('@fullcalendar/react', () => ({
  __esModule: true,
  default: (props: StubFullCalendarProps) => (
    <div
      data-testid="fullcalendar-stub"
      data-first-day={String(props.firstDay ?? 0)}
    >
      <button
        data-testid="simulate-dates-set-tuesday"
        onClick={() => {
          // Simulate FullCalendar navigating to a week that contains Tue Apr 21 2026
          // (a mid-week date). FullCalendar with firstDay=1 would pass a Monday
          // here, but the CalendarView logic independently re-aligns to Monday
          // via startOfWeek(weekStartsOn: 1), which is what we want to verify.
          // We construct dates using the local-time constructor so the test is
          // timezone-independent.
          props.datesSet?.({
            start: new Date(2026, 3, 21, 12, 0, 0), // Tue Apr 21 2026 local
            end: new Date(2026, 3, 28, 12, 0, 0),
            startStr: '2026-04-21',
            endStr: '2026-04-28',
            timeZone: 'local',
            view: {},
          });
        }}
      >
        fire datesSet mid-week
      </button>
      <button
        data-testid="simulate-dates-set-next-monday"
        onClick={() => {
          // Simulate FullCalendar emitting datesSet after "next" is pressed —
          // landing on Mon Apr 27 2026 (one week after Mon Apr 20 2026).
          props.datesSet?.({
            start: new Date(2026, 3, 27, 12, 0, 0), // Mon Apr 27 2026 local
            end: new Date(2026, 4, 4, 12, 0, 0),
            startStr: '2026-04-27',
            endStr: '2026-05-04',
            timeZone: 'local',
            view: {},
          });
        }}
      >
        fire datesSet next week
      </button>
    </div>
  ),
}));
vi.mock('@fullcalendar/daygrid', () => ({ __esModule: true, default: {} }));
vi.mock('@fullcalendar/timegrid', () => ({ __esModule: true, default: {} }));
vi.mock('@fullcalendar/interaction', () => ({ __esModule: true, default: {} }));

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
  mockUseWeeklySchedule.mockReturnValue({
    data: { days: [] },
    isLoading: false,
    error: null,
  });
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe('CalendarView — Monday-based weeks (H-3)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupDefaultMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('week grid starts on Monday given a mid-week date', () => {
    // Freeze "today" to Tuesday, April 21, 2026 (local time). The preceding
    // Monday is April 20, 2026 — that is what CalendarView should align to
    // when it derives the initial week range for useWeeklySchedule.
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 3, 21, 12, 0, 0));

    render(<CalendarView />, { wrapper: createWrapper() });

    expect(mockUseWeeklySchedule).toHaveBeenCalled();
    const [startDate] = mockUseWeeklySchedule.mock.calls[0];
    // Monday of the week containing Tue Apr 21 2026.
    expect(startDate).toBe('2026-04-20');

    // And the FullCalendar grid itself must be told to render Monday-first.
    const stub = screen.getByTestId('fullcalendar-stub');
    expect(stub).toHaveAttribute('data-first-day', '1');
  });

  it('adjacent week navigation jumps by 7 days from Monday to Monday', async () => {
    const user = userEvent.setup();
    const onWeekChange = vi.fn();

    render(<CalendarView onWeekChange={onWeekChange} />, {
      wrapper: createWrapper(),
    });

    // Simulate FullCalendar emitting datesSet for the mid-week range first,
    // followed by the "next week" navigation. CalendarView must round each
    // arg.start down to the preceding Monday and the two Mondays must be
    // exactly 7 days apart.
    await user.click(screen.getByTestId('simulate-dates-set-tuesday'));
    await user.click(screen.getByTestId('simulate-dates-set-next-monday'));

    expect(onWeekChange).toHaveBeenCalledTimes(2);
    const firstMonday: Date = onWeekChange.mock.calls[0][0];
    const secondMonday: Date = onWeekChange.mock.calls[1][0];

    // Both callbacks received a Monday (getDay === 1).
    expect(firstMonday.getDay()).toBe(1);
    expect(secondMonday.getDay()).toBe(1);

    // Exactly 7 days apart, Monday → Monday.
    const msPerDay = 1000 * 60 * 60 * 24;
    const diffDays = Math.round(
      (secondMonday.getTime() - firstMonday.getTime()) / msPerDay,
    );
    expect(diffDays).toBe(7);
  });
});
