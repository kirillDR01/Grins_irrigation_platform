/**
 * MonthMode — month-at-a-glance density grid: techs as rows × days as cols.
 *
 * Each `[tech × day]` cell shows the count of non-cancelled appointments
 * for that tech on that day. Background scales with count:
 *   0   → bg-slate-50
 *   1–2 → bg-emerald-100
 *   3–5 → bg-emerald-300
 *   6+  → bg-emerald-500 text-white
 *
 * Clicking a cell drills into Day mode for that date (any tech).
 *
 * Data: fans out one weekly query per ISO-week that overlaps the visible
 * month via TanStack `useQueries`. Reuses `appointmentKeys.weekly(start)`
 * cache entries so a recent Week-mode visit pre-warms the grid.
 */

import { useMemo, type CSSProperties } from 'react';
import { useQueries } from '@tanstack/react-query';
import {
  addDays,
  eachDayOfInterval,
  endOfMonth,
  format,
  isSameMonth,
  isSameDay,
  parseISO,
  startOfMonth,
  startOfWeek,
} from 'date-fns';
import { useStaff } from '@/features/staff/hooks/useStaff';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import { appointmentApi } from '../../api/appointmentApi';
import { appointmentKeys } from '../../hooks/useAppointments';
import { TechHeader } from './TechHeader';
import type { WeeklyScheduleResponse } from '../../types';

export interface MonthModeProps {
  /** Any date inside the month to render. */
  date: Date;
  /** Drill into Day mode for the clicked date. */
  onDayHeaderClick: (isoDate: string) => void;
}

function densityClass(count: number): string {
  if (count === 0) return 'bg-slate-50 text-slate-300';
  if (count <= 2) return 'bg-emerald-100 text-emerald-900';
  if (count <= 5) return 'bg-emerald-300 text-emerald-950';
  return 'bg-emerald-500 text-white';
}

export function MonthMode({ date, onDayHeaderClick }: MonthModeProps) {
  const today = useMemo(() => new Date(), []);

  const monthStart = useMemo(() => startOfMonth(date), [date]);
  const monthEnd = useMemo(() => endOfMonth(date), [date]);

  // Weekly fan-out covers the whole month — start each week on Monday so
  // we land on the same day-of-week the BE expects (any day works; we
  // only consume the returned days).
  const weekStarts = useMemo(() => {
    const firstWeek = startOfWeek(monthStart, { weekStartsOn: 1 });
    const out: string[] = [];
    let cursor = firstWeek;
    while (cursor <= monthEnd) {
      out.push(format(cursor, 'yyyy-MM-dd'));
      cursor = addDays(cursor, 7);
    }
    return out;
  }, [monthStart, monthEnd]);

  const weeklyQueries = useQueries({
    queries: weekStarts.map((startDate) => ({
      queryKey: appointmentKeys.weekly(startDate, undefined),
      queryFn: () => appointmentApi.getWeeklySchedule(startDate),
      staleTime: 30_000,
    })),
  });

  const isLoadingWeeks = weeklyQueries.some((q) => q.isLoading);
  const isErrorWeeks = weeklyQueries.some((q) => q.isError);

  const {
    data: staffData,
    isLoading: isLoadingStaff,
    isError: isErrorStaff,
  } = useStaff({ page_size: 100 });

  // Days of the visible month (1..28-31).
  const monthDays = useMemo(
    () => eachDayOfInterval({ start: monthStart, end: monthEnd }),
    [monthStart, monthEnd]
  );

  // Bucket counts: counts[staffId][isoDate] = number of non-cancelled appointments.
  const counts = useMemo(() => {
    const out: Record<string, Record<string, number>> = {};
    for (const q of weeklyQueries) {
      const data = q.data as WeeklyScheduleResponse | undefined;
      if (!data?.days) continue;
      for (const day of data.days) {
        // Skip days outside the visible month so neighboring weeks don't
        // contaminate the bucket.
        const d = parseISO(day.date);
        if (!isSameMonth(d, monthStart)) continue;
        for (const apt of day.appointments) {
          if (apt.status === 'cancelled') continue;
          const byDate = out[apt.staff_id] ?? (out[apt.staff_id] = {});
          byDate[apt.scheduled_date] = (byDate[apt.scheduled_date] ?? 0) + 1;
        }
      }
    }
    return out;
  }, [weeklyQueries, monthStart]);

  if (isLoadingWeeks || isLoadingStaff) {
    return (
      <div
        data-testid="schedule-month-mode"
        className="flex items-center justify-center h-96"
      >
        <LoadingSpinner />
      </div>
    );
  }

  if (isErrorWeeks || isErrorStaff) {
    return (
      <div
        data-testid="schedule-month-mode"
        className="p-6 text-center text-rose-600"
      >
        Failed to load schedule.
      </div>
    );
  }

  const techs = (staffData?.items ?? []).filter(
    (s) => s.is_active && s.role === 'tech'
  );

  if (techs.length === 0) {
    return (
      <div
        data-testid="schedule-empty-state"
        className="p-8 text-center text-slate-500"
      >
        No technicians available — add staff in Settings.
      </div>
    );
  }

  const gridStyle: CSSProperties = {
    gridTemplateColumns: `200px repeat(${monthDays.length}, minmax(28px, 1fr))`,
  };

  return (
    <div
      data-testid="schedule-month-mode"
      className="grid w-full overflow-x-auto"
      style={gridStyle}
    >
      {/* Top-left corner */}
      <div className="border-b border-slate-100 bg-slate-50 p-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        Resources
      </div>
      {/* Day-of-month header row */}
      {monthDays.map((d) => {
        const isToday = isSameDay(d, today);
        const iso = format(d, 'yyyy-MM-dd');
        const dow = format(d, 'EEEEE'); // single-letter weekday: M T W T F S S
        const dom = format(d, 'd');
        return (
          <button
            key={`hdr-${iso}`}
            type="button"
            data-testid={`month-header-${iso}`}
            onClick={() => onDayHeaderClick(iso)}
            className={`flex flex-col items-center justify-center border-b border-slate-100 px-1 py-1 text-[10px] font-semibold uppercase tracking-wider hover:bg-slate-100 ${
              isToday ? 'bg-teal-50 text-teal-700' : 'text-slate-500'
            }`}
            aria-label={`Drill into day ${format(d, 'MMMM d')}`}
          >
            <span>{dow}</span>
            <span className="text-[12px] text-slate-700">{dom}</span>
          </button>
        );
      })}

      {/* Tech rows */}
      {techs.map((staff) => (
        <div key={`row-${staff.id}`} className="contents">
          <TechHeader staff={staff} utilizationPct={null} />
          {monthDays.map((d) => {
            const iso = format(d, 'yyyy-MM-dd');
            const count = counts[staff.id]?.[iso] ?? 0;
            const isToday = isSameDay(d, today);
            return (
              <button
                key={`cell-${staff.id}-${iso}`}
                type="button"
                data-testid={`month-cell-${staff.id}-${iso}`}
                onClick={() => onDayHeaderClick(iso)}
                className={`flex items-center justify-center border-b border-l border-slate-100 text-sm font-semibold transition-colors ${densityClass(
                  count
                )} ${isToday ? 'ring-2 ring-inset ring-teal-300' : ''}`}
                aria-label={`${staff.name} — ${count} appointment${
                  count === 1 ? '' : 's'
                } on ${format(d, 'MMMM d')}`}
              >
                {count > 0 ? count : ''}
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}
