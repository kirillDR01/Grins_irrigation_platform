/**
 * MonthMode tests — render, density-color-by-count, drill-in-on-click,
 * loading + empty states.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { Appointment, WeeklyScheduleResponse } from '../../types';
import type { Staff } from '@/features/staff/types';

const mockUseQueries = vi.fn();
const mockUseStaff = vi.fn();

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('@tanstack/react-query')>();
  return {
    ...actual,
    useQueries: (...args: unknown[]) => mockUseQueries(...args),
  };
});
vi.mock('@/features/staff/hooks/useStaff', () => ({
  useStaff: (...args: unknown[]) => mockUseStaff(...args),
}));

import { MonthMode } from './MonthMode';

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

/**
 * Build weekly responses that span the visible month. The component fans
 * out one weekly query per ISO-week covering [monthStart..monthEnd]; each
 * stub returns the corresponding 7-day window. Tests can override the
 * `appointments` list of any single day via `apptsByDate`.
 */
function buildWeeklyStubs(
  weekStarts: string[],
  apptsByDate: Record<string, Appointment[]>
): Array<{ data: WeeklyScheduleResponse; isLoading: false; isError: false }> {
  return weekStarts.map((startDateStr) => {
    const start = new Date(`${startDateStr}T00:00:00`);
    const days = Array.from({ length: 7 }, (_, i) => {
      const d = new Date(start);
      d.setDate(d.getDate() + i);
      const iso = d.toISOString().slice(0, 10);
      return {
        date: iso,
        appointments: apptsByDate[iso] ?? [],
        total_count: (apptsByDate[iso] ?? []).length,
      };
    });
    const endIso = (() => {
      const e = new Date(start);
      e.setDate(e.getDate() + 6);
      return e.toISOString().slice(0, 10);
    })();
    return {
      data: {
        start_date: startDateStr,
        end_date: endIso,
        days,
        total_appointments: days.reduce((s, d) => s + d.appointments.length, 0),
      },
      isLoading: false,
      isError: false,
    };
  });
}

// Visible month: April 2026 (April 30 is "today" per memory). Anchor any
// date inside the month; the component derives monthStart/monthEnd itself.
const TARGET_DATE = new Date(2026, 3, 15); // 2026-04-15
// startOfWeek(2026-04-01, weekStartsOn:1) = Mon 2026-03-30; iterate by 7d
// until > 2026-04-30. That's: 2026-03-30, 2026-04-06, 2026-04-13,
// 2026-04-20, 2026-04-27 → five weeks.
const APRIL_WEEK_STARTS = [
  '2026-03-30',
  '2026-04-06',
  '2026-04-13',
  '2026-04-20',
  '2026-04-27',
];

describe('MonthMode', () => {
  beforeEach(() => {
    mockUseStaff.mockReturnValue({
      data: { items: mockStaff, total: 2, page: 1, page_size: 100, total_pages: 1 },
      isLoading: false,
      isError: false,
    });
    mockUseQueries.mockReturnValue(buildWeeklyStubs(APRIL_WEEK_STARTS, {}));
  });

  it('renders the month-mode root and one row per active tech', () => {
    render(
      <MonthMode date={TARGET_DATE} onDayHeaderClick={vi.fn()} />,
      { wrapper }
    );
    expect(screen.getByTestId('schedule-month-mode')).toBeInTheDocument();
    expect(screen.getByTestId('tech-header-staff-1')).toBeInTheDocument();
    expect(screen.getByTestId('tech-header-staff-2')).toBeInTheDocument();
  });

  it('renders one column header per day of the visible month', () => {
    render(
      <MonthMode date={TARGET_DATE} onDayHeaderClick={vi.fn()} />,
      { wrapper }
    );
    // April 2026 has 30 days
    expect(screen.getByTestId('month-header-2026-04-01')).toBeInTheDocument();
    expect(screen.getByTestId('month-header-2026-04-15')).toBeInTheDocument();
    expect(screen.getByTestId('month-header-2026-04-30')).toBeInTheDocument();
    expect(screen.queryByTestId('month-header-2026-05-01')).toBeNull();
    expect(screen.queryByTestId('month-header-2026-03-31')).toBeNull();
  });

  it('renders one [tech × day] cell per tech-day pair', () => {
    render(
      <MonthMode date={TARGET_DATE} onDayHeaderClick={vi.fn()} />,
      { wrapper }
    );
    expect(
      screen.getByTestId('month-cell-staff-1-2026-04-01')
    ).toBeInTheDocument();
    expect(
      screen.getByTestId('month-cell-staff-2-2026-04-30')
    ).toBeInTheDocument();
  });

  it('paints density backgrounds by appointment count thresholds', () => {
    // staff-1 buckets: 0 / 1 / 3 / 6 across four April dates.
    // 2026-04-01 → empty (0)
    // 2026-04-02 → 1 appointment
    // 2026-04-03 → 3 appointments
    // 2026-04-04 → 6 appointments
    const apptsByDate: Record<string, Appointment[]> = {
      '2026-04-02': [
        { ...baseAppt, id: 'a1', staff_id: 'staff-1', scheduled_date: '2026-04-02' },
      ],
      '2026-04-03': Array.from({ length: 3 }, (_, i) => ({
        ...baseAppt,
        id: `b${i}`,
        staff_id: 'staff-1',
        scheduled_date: '2026-04-03',
      })),
      '2026-04-04': Array.from({ length: 6 }, (_, i) => ({
        ...baseAppt,
        id: `c${i}`,
        staff_id: 'staff-1',
        scheduled_date: '2026-04-04',
      })),
    };
    mockUseQueries.mockReturnValue(
      buildWeeklyStubs(APRIL_WEEK_STARTS, apptsByDate)
    );

    render(
      <MonthMode date={TARGET_DATE} onDayHeaderClick={vi.fn()} />,
      { wrapper }
    );

    const empty = screen.getByTestId('month-cell-staff-1-2026-04-01');
    const low = screen.getByTestId('month-cell-staff-1-2026-04-02');
    const mid = screen.getByTestId('month-cell-staff-1-2026-04-03');
    const high = screen.getByTestId('month-cell-staff-1-2026-04-04');

    expect(empty.className).toMatch(/bg-slate-50/);
    expect(low.className).toMatch(/bg-emerald-100/);
    expect(mid.className).toMatch(/bg-emerald-300/);
    expect(high.className).toMatch(/bg-emerald-500/);
    // Counts render as visible text on non-empty cells only.
    expect(empty.textContent).toBe('');
    expect(low.textContent).toContain('1');
    expect(mid.textContent).toContain('3');
    expect(high.textContent).toContain('6');
  });

  it('excludes cancelled appointments from the density count', () => {
    const apptsByDate: Record<string, Appointment[]> = {
      '2026-04-10': [
        { ...baseAppt, id: 'live', staff_id: 'staff-1', scheduled_date: '2026-04-10' },
        {
          ...baseAppt,
          id: 'dead',
          staff_id: 'staff-1',
          scheduled_date: '2026-04-10',
          status: 'cancelled',
        },
      ],
    };
    mockUseQueries.mockReturnValue(
      buildWeeklyStubs(APRIL_WEEK_STARTS, apptsByDate)
    );

    render(
      <MonthMode date={TARGET_DATE} onDayHeaderClick={vi.fn()} />,
      { wrapper }
    );
    const cell = screen.getByTestId('month-cell-staff-1-2026-04-10');
    expect(cell.textContent).toContain('1');
  });

  it('drills into Day mode when a cell is clicked', () => {
    const onDrillIn = vi.fn();
    render(
      <MonthMode date={TARGET_DATE} onDayHeaderClick={onDrillIn} />,
      { wrapper }
    );
    fireEvent.click(screen.getByTestId('month-cell-staff-1-2026-04-15'));
    expect(onDrillIn).toHaveBeenCalledWith('2026-04-15');
  });

  it('drills into Day mode when a column header is clicked', () => {
    const onDrillIn = vi.fn();
    render(
      <MonthMode date={TARGET_DATE} onDayHeaderClick={onDrillIn} />,
      { wrapper }
    );
    fireEvent.click(screen.getByTestId('month-header-2026-04-07'));
    expect(onDrillIn).toHaveBeenCalledWith('2026-04-07');
  });

  it('renders the loading spinner while weekly queries load', () => {
    mockUseQueries.mockReturnValue([
      { data: undefined, isLoading: true, isError: false },
    ]);
    render(
      <MonthMode date={TARGET_DATE} onDayHeaderClick={vi.fn()} />,
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
      <MonthMode date={TARGET_DATE} onDayHeaderClick={vi.fn()} />,
      { wrapper }
    );
    expect(screen.getByTestId('schedule-empty-state')).toBeInTheDocument();
  });

  it('renders the error state when a weekly query fails', () => {
    mockUseQueries.mockReturnValue([
      { data: undefined, isLoading: false, isError: true },
    ]);
    render(
      <MonthMode date={TARGET_DATE} onDayHeaderClick={vi.fn()} />,
      { wrapper }
    );
    expect(screen.getByText('Failed to load schedule.')).toBeInTheDocument();
  });
});
