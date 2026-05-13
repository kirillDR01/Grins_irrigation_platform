/**
 * WeekMode — the headline view: techs as rows × 7 days as columns.
 *
 * Each `[tech × day]` cell contains a 16px sparkline at the top and
 * stacked AppointmentCards below in ascending start-time order. Drag
 * across cells reassigns staff and/or scheduled date (time stays the
 * same in week mode); the time-precise reschedule lives in DayMode.
 *
 * Today's column is tinted teal-50 for at-a-glance orientation; the
 * capacity footer paints orange ≥85%, teal otherwise.
 */

import { useMemo, type CSSProperties } from 'react';
import { addDays, format, isSameDay, parseISO } from 'date-fns';
import { toast } from 'sonner';
import { useStaff } from '@/features/staff/hooks/useStaff';
import { useWeeklySchedule } from '../../hooks/useAppointments';
import { useUpdateAppointment } from '../../hooks/useAppointmentMutations';
import { useWeeklyUtilization } from '../../hooks/useWeeklyUtilization';
import { useWeeklyCapacity } from '../../hooks/useWeeklyCapacity';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import { AppointmentCard } from './AppointmentCard';
import { CapacityFooter } from './CapacityFooter';
import { DayHeader } from './DayHeader';
import { SparklineBar } from './SparklineBar';
import { TechHeader } from './TechHeader';
import type { Appointment } from '../../types';
import type { DragPayload } from './types';

export interface WeekModeProps {
  weekStart: Date;
  selectedDate: Date | null;
  onAppointmentClick: (id: string) => void;
  onEmptyCellClick: (staffId: string, date: string) => void;
  onDayHeaderClick: (date: string) => void;
}

export function WeekMode({
  weekStart,
  selectedDate,
  onAppointmentClick,
  onEmptyCellClick,
  onDayHeaderClick,
}: WeekModeProps) {
  const dates = useMemo(
    () =>
      Array.from({ length: 7 }, (_, i) =>
        format(addDays(weekStart, i), 'yyyy-MM-dd')
      ),
    [weekStart]
  );

  const startDateStr = dates[0]!;
  const endDateStr = format(addDays(weekStart, 7), 'yyyy-MM-dd');

  const {
    data: weeklySchedule,
    isLoading: isLoadingSchedule,
    isError: isErrorSchedule,
  } = useWeeklySchedule(startDateStr, endDateStr);

  const {
    data: staffData,
    isLoading: isLoadingStaff,
    isError: isErrorStaff,
  } = useStaff({ page_size: 100 });

  const utilization = useWeeklyUtilization(weekStart);
  const capacity = useWeeklyCapacity(weekStart);
  const updateAppointment = useUpdateAppointment();

  const today = useMemo(() => new Date(), []);
  const selectedDateStr = selectedDate
    ? format(selectedDate, 'yyyy-MM-dd')
    : null;

  // Filter cancelled and bucket by [staffId][date].
  const buckets = useMemo(() => {
    const out: Record<string, Record<string, Appointment[]>> = {};
    if (!weeklySchedule?.days) return out;
    for (const day of weeklySchedule.days) {
      for (const apt of day.appointments) {
        if (apt.status === 'cancelled') continue;
        const byDate = out[apt.staff_id] ?? (out[apt.staff_id] = {});
        const list = byDate[apt.scheduled_date] ?? (byDate[apt.scheduled_date] = []);
        list.push(apt);
      }
    }
    // Sort each list by start time.
    for (const byDate of Object.values(out)) {
      for (const list of Object.values(byDate)) {
        list.sort((a, b) =>
          a.time_window_start.localeCompare(b.time_window_start)
        );
      }
    }
    return out;
  }, [weeklySchedule]);

  // Per-day job count (excluding cancelled) for the column header.
  const jobCountByDate = useMemo(() => {
    const out: Record<string, number> = {};
    if (!weeklySchedule?.days) return out;
    for (const day of weeklySchedule.days) {
      out[day.date] = day.appointments.filter(
        (a) => a.status !== 'cancelled'
      ).length;
    }
    return out;
  }, [weeklySchedule]);

  // Drafts grouped by day for SendDayConfirmationsButton (parity).
  const draftsByDay = useMemo(() => {
    const map: Record<string, Appointment[]> = {};
    if (!weeklySchedule?.days) return map;
    for (const day of weeklySchedule.days) {
      const drafts = day.appointments.filter((a) => a.status === 'draft');
      if (drafts.length > 0) {
        map[day.date] = drafts;
      }
    }
    return map;
  }, [weeklySchedule]);

  // Per-tech (per-row) week utilization average across the 7 days.
  const utilizationByTech = useMemo(() => {
    const out: Record<string, number | null> = {};
    if (utilization.isLoading) return out;
    const totals: Record<string, { sum: number; count: number }> = {};
    for (const day of utilization.days) {
      if (!day) continue;
      for (const r of day.resources) {
        const t = totals[r.staff_id] ?? (totals[r.staff_id] = { sum: 0, count: 0 });
        t.sum += r.utilization_pct;
        t.count += 1;
      }
    }
    for (const [staffId, { sum, count }] of Object.entries(totals)) {
      out[staffId] = count > 0 ? sum / count : 0;
    }
    return out;
  }, [utilization.days, utilization.isLoading]);

  // Per-day average capacity (across all resources in the day).
  const capacityByDate = useMemo(() => {
    const out: Record<string, number | null> = {};
    dates.forEach((d, i) => {
      const day = capacity.days[i];
      if (!day) {
        out[d] = capacity.isLoading ? null : 0;
        return;
      }
      out[d] = day.utilization_pct ?? 0;
    });
    return out;
  }, [capacity.days, capacity.isLoading, dates]);

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleCellDrop = async (
    e: React.DragEvent<HTMLDivElement>,
    cellStaffId: string,
    cellDate: string
  ) => {
    e.preventDefault();
    const raw = e.dataTransfer.getData('application/json');
    if (!raw) return;
    let payload: DragPayload;
    try {
      payload = JSON.parse(raw) as DragPayload;
    } catch {
      return;
    }
    if (
      payload.originStaffId === cellStaffId &&
      payload.originDate === cellDate
    ) {
      return;
    }
    try {
      await updateAppointment.mutateAsync({
        id: payload.appointmentId,
        data: {
          staff_id: cellStaffId,
          scheduled_date: cellDate,
          // Cluster D Item 1: drag-drop must not silently text the customer.
          // The backend still demotes CONFIRMED → SCHEDULED; admin must
          // explicitly click Send afterwards.
          suppress_notifications: true,
        },
      });
      toast.success('Appointment updated');
    } catch (error: unknown) {
      const is409 =
        typeof error === 'object' &&
        error !== null &&
        'response' in error &&
        (error as { response?: { status?: number } }).response?.status === 409;
      toast.error(
        is409
          ? 'Scheduling conflict — that tech is already booked'
          : 'Update failed'
      );
    }
  };

  if (isLoadingSchedule || isLoadingStaff) {
    return (
      <div
        data-testid="schedule-week-mode"
        className="flex items-center justify-center h-96"
      >
        <LoadingSpinner />
      </div>
    );
  }

  if (isErrorSchedule || isErrorStaff) {
    return (
      <div
        data-testid="schedule-week-mode"
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

  // CSS Grid: 200px tech-header column + 7 equal day columns.
  const gridStyle: CSSProperties = {
    gridTemplateColumns: '200px repeat(7, minmax(72px, 1fr))',
  };

  return (
    <div
      data-testid="schedule-week-mode"
      className="grid w-full"
      style={gridStyle}
    >
      {/* Top-left corner */}
      <div className="border-b border-slate-100 bg-slate-50 p-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        Resources
      </div>
      {/* Day headers */}
      {dates.map((date) => {
        const isToday = isSameDay(parseISO(date), today);
        return (
          <div
            key={`hdr-${date}`}
            className={isToday ? 'bg-teal-50' : ''}
          >
            <DayHeader
              date={date}
              jobCount={jobCountByDate[date] ?? 0}
              isToday={isToday}
              draftAppointments={draftsByDay[date] ?? []}
              onDrillIn={onDayHeaderClick}
            />
          </div>
        );
      })}

      {/* Tech rows */}
      {techs.map((staff) => {
        const fromMap = utilizationByTech[staff.id];
        // Reserve `null` for the genuine loading state. After settle,
        // a missing entry means the BE returned no row for that tech →
        // render 0%, not the loading skeleton.
        const utilPct = utilization.isLoading ? null : (fromMap ?? 0);
        return (
          <div
            key={`row-${staff.id}`}
            className="contents"
          >
            <TechHeader staff={staff} utilizationPct={utilPct} />
            {dates.map((date) => {
              const isToday = isSameDay(parseISO(date), today);
              const cellAppts = buckets[staff.id]?.[date] ?? [];
              const cellBg = isToday ? 'bg-teal-50/50' : '';
              return (
                <div
                  key={`cell-${staff.id}-${date}`}
                  data-testid={`cell-${staff.id}-${date}`}
                  className={`min-h-[120px] border-b border-l border-slate-100 p-1 ${cellBg}`}
                  onDragOver={handleDragOver}
                  onDrop={(e) => handleCellDrop(e, staff.id, date)}
                  onClick={(e) => {
                    if (e.target === e.currentTarget) {
                      onEmptyCellClick(staff.id, date);
                    }
                  }}
                >
                  <SparklineBar
                    appointments={cellAppts}
                    staffId={staff.id}
                    date={date}
                  />
                  <div className="mt-1 flex flex-col gap-1">
                    {cellAppts.map((appt) => (
                      <AppointmentCard
                        key={appt.id}
                        appointment={appt}
                        variant="stacked"
                        isOnSelectedDate={
                          selectedDateStr === appt.scheduled_date
                        }
                        onAppointmentClick={onAppointmentClick}
                      />
                    ))}
                    {cellAppts.length === 0 && (
                      <button
                        type="button"
                        onClick={() => onEmptyCellClick(staff.id, date)}
                        className="mt-2 h-8 w-full rounded border border-dashed border-slate-200 text-[11px] text-slate-400 hover:border-teal-300 hover:text-teal-600 hover:bg-teal-50/40"
                        aria-label={`Create appointment for ${staff.name} on ${date}`}
                      >
                        +
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        );
      })}

      {/* Capacity footer */}
      <div className="border-t border-slate-100 bg-slate-50 p-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        Capacity
      </div>
      {dates.map((date) => (
        <div
          key={`cap-${date}`}
          className="border-t border-l border-slate-100 p-2"
        >
          <CapacityFooter
            date={date}
            capacityPct={capacityByDate[date] ?? null}
          />
        </div>
      ))}
    </div>
  );
}
