/**
 * DayMode — single-date, all-techs horizontal time grid.
 *
 * Layout: CSS Grid with a 200px tech-header column and a single 1fr
 * time-axis column. Each tech-row strip is a `position: relative` drop
 * zone; appointments render as absolute-positioned `<AppointmentCard
 * variant='absolute'>`s, with x = `minutesToPercent(start)`%, width =
 * span%, and top = `lane * 38px`. Lanes are computed *per-tech* via
 * `assignLanes` so two overlapping appointments on the same tech stack
 * vertically rather than overlap.
 *
 * Drag-drop:
 *  - Same-row drop = reschedule (PATCH `time_window_start/end`, snapped
 *    to 15min, duration preserved, past-8pm rejected with toast).
 *  - Different-row drop = reassign + reschedule combined PATCH.
 *  - Both branches always include `staff_id` + `scheduled_date` (no-op
 *    if same) — keeps the PATCH payload uniform.
 *
 * NowLine renders only when `date` equals today and now is within the
 * 6am-8pm visible window.
 */

import { useMemo, type CSSProperties } from 'react';
import { format, isSameDay } from 'date-fns';
import { toast } from 'sonner';
import { useStaff } from '@/features/staff/hooks/useStaff';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import { useDailySchedule } from '../../hooks/useAppointments';
import { useUpdateAppointment } from '../../hooks/useAppointmentMutations';
import { useUtilizationReport } from '../../hooks/useAIScheduling';
import { AppointmentCard } from './AppointmentCard';
import { NowLine } from './NowLine';
import { TechHeader } from './TechHeader';
import {
  DAY_END_MIN,
  DAY_SPAN_MIN,
  DAY_START_MIN,
  assignLanes,
  minutesToPercent,
  timeToMinutes,
} from './utils';
import type { Appointment } from '../../types';
import type { DragPayload } from './types';

export interface DayModeProps {
  date: Date;
  selectedDate: Date | null;
  onAppointmentClick: (id: string) => void;
  onEmptyCellClick: (staffId: string, date: string) => void;
}

/** Hour-axis ticks: every hour from 6am through 8pm inclusive (15 ticks). */
const HOUR_TICKS = Array.from(
  { length: DAY_SPAN_MIN / 60 + 1 },
  (_, i) => DAY_START_MIN + i * 60
);

const LANE_HEIGHT_PX = 38;
const CARD_HEIGHT_PX = 36;
const MIN_STRIP_HEIGHT_PX = 80;
const SNAP_MINUTES = 15;

function formatHourLabel(min: number): string {
  const h = Math.floor(min / 60);
  if (h === 0) return '12am';
  if (h < 12) return `${h}am`;
  if (h === 12) return '12pm';
  return `${h - 12}pm`;
}

function pad2(n: number): string {
  return n.toString().padStart(2, '0');
}

function minutesToTimeString(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `${pad2(h)}:${pad2(m)}:00`;
}

export function DayMode({
  date,
  selectedDate,
  onAppointmentClick,
  onEmptyCellClick,
}: DayModeProps) {
  const dateStr = useMemo(() => format(date, 'yyyy-MM-dd'), [date]);

  const {
    data: dailySchedule,
    isLoading: isLoadingSchedule,
    isError: isErrorSchedule,
  } = useDailySchedule(dateStr);

  const {
    data: staffData,
    isLoading: isLoadingStaff,
    isError: isErrorStaff,
  } = useStaff({ page_size: 100 });

  const { data: utilization, isLoading: isLoadingUtilization } =
    useUtilizationReport(dateStr);
  const updateAppointment = useUpdateAppointment();

  const isToday = useMemo(() => isSameDay(date, new Date()), [date]);

  const selectedDateStr = selectedDate
    ? format(selectedDate, 'yyyy-MM-dd')
    : null;

  // Bucket non-cancelled appointments by staff_id.
  const apptsByTech = useMemo(() => {
    const out: Record<string, Appointment[]> = {};
    if (!dailySchedule?.appointments) return out;
    for (const apt of dailySchedule.appointments) {
      if (apt.status === 'cancelled') continue;
      const list = out[apt.staff_id] ?? (out[apt.staff_id] = []);
      list.push(apt);
    }
    return out;
  }, [dailySchedule]);

  const utilizationByTech = useMemo(() => {
    const out: Record<string, number | null> = {};
    if (!utilization) return out;
    for (const r of utilization.resources) {
      out[r.staff_id] = r.utilization_pct;
    }
    return out;
  }, [utilization]);

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleRowDrop = async (
    e: React.DragEvent<HTMLDivElement>,
    cellStaffId: string
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

    // Compute new start time from the drop X coordinate inside the strip.
    const rect = e.currentTarget.getBoundingClientRect();
    const xPct = rect.width > 0 ? (e.clientX - rect.left) / rect.width : 0;
    const clampedXPct = Math.min(Math.max(xPct, 0), 1);
    const rawMin = DAY_START_MIN + clampedXPct * DAY_SPAN_MIN;
    const snappedStart =
      Math.round(rawMin / SNAP_MINUTES) * SNAP_MINUTES;

    const durMin =
      timeToMinutes(payload.originEndTime) -
      timeToMinutes(payload.originStartTime);
    const newStartMin = snappedStart;
    const newEndMin = newStartMin + durMin;

    if (newStartMin < DAY_START_MIN) {
      toast.error('Cannot schedule before 6am');
      return;
    }
    if (newEndMin > DAY_END_MIN) {
      toast.error('Cannot schedule past 8pm — pick an earlier slot');
      return;
    }

    const sameStaff = payload.originStaffId === cellStaffId;
    const sameDate = payload.originDate === dateStr;
    const sameStart =
      timeToMinutes(payload.originStartTime) === newStartMin;
    if (sameStaff && sameDate && sameStart) {
      return; // No-op
    }

    const newStartTime = minutesToTimeString(newStartMin);
    const newEndTime = minutesToTimeString(newEndMin);

    try {
      await updateAppointment.mutateAsync({
        id: payload.appointmentId,
        data: {
          staff_id: cellStaffId,
          scheduled_date: dateStr,
          time_window_start: newStartTime,
          time_window_end: newEndTime,
        },
      });
      toast.success(
        !sameStaff ? 'Reassigned and rescheduled' : 'Rescheduled'
      );
    } catch (error: unknown) {
      const is409 =
        typeof error === 'object' &&
        error !== null &&
        'response' in error &&
        (error as { response?: { status?: number } }).response?.status === 409;
      toast.error(
        is409
          ? 'Scheduling conflict — that tech is already booked'
          : `Failed to update: ${
              error instanceof Error ? error.message : 'unknown error'
            }`
      );
    }
  };

  if (isLoadingSchedule || isLoadingStaff) {
    return (
      <div
        data-testid="schedule-day-mode"
        className="flex items-center justify-center h-96"
      >
        <LoadingSpinner />
      </div>
    );
  }

  if (isErrorSchedule || isErrorStaff) {
    return (
      <div
        data-testid="schedule-day-mode"
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
    gridTemplateColumns: '200px minmax(0, 1fr)',
  };

  return (
    <div
      data-testid="schedule-day-mode"
      className="grid w-full"
      style={gridStyle}
    >
      {/* Top-left corner */}
      <div className="border-b border-slate-100 bg-slate-50 p-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        Resources
      </div>
      {/* Hour-axis ruler */}
      <div className="relative h-10 border-b border-slate-100 bg-slate-50">
        {HOUR_TICKS.map((min) => {
          const isMajor = (min / 60) % 2 === 0;
          const leftPct = minutesToPercent(min);
          return (
            <div
              key={`tick-${min}`}
              data-testid={`hour-tick-${min}`}
              className="absolute top-0 bottom-0 border-l border-slate-200"
              style={{ left: `${leftPct}%` }}
            >
              {isMajor && (
                <span className="absolute top-1 left-1 text-[10px] font-semibold text-slate-500">
                  {formatHourLabel(min)}
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Tech rows */}
      {techs.map((staff) => {
        const fromMap = utilizationByTech[staff.id];
        // Reserve `null` for the genuine loading state. After settle,
        // a missing entry means the BE returned no row for that tech →
        // render 0%, not the loading skeleton.
        const utilPct = isLoadingUtilization ? null : (fromMap ?? 0);
        const techAppts = apptsByTech[staff.id] ?? [];
        const positioned = assignLanes(
          techAppts.map((apt) => ({
            apt,
            start: timeToMinutes(apt.time_window_start),
            end: timeToMinutes(apt.time_window_end),
          }))
        );
        const laneCount = positioned.reduce(
          (max, p) => Math.max(max, p.lane + 1),
          0
        );
        const stripHeight = Math.max(
          MIN_STRIP_HEIGHT_PX,
          laneCount * LANE_HEIGHT_PX + 4
        );
        return (
          <div key={`row-${staff.id}`} className="contents">
            <TechHeader staff={staff} utilizationPct={utilPct} />
            <div
              data-testid={`cell-${staff.id}-${dateStr}`}
              className="relative border-b border-l border-slate-100"
              style={{ height: `${stripHeight}px` }}
              onDragOver={handleDragOver}
              onDrop={(e) => handleRowDrop(e, staff.id)}
              onClick={(e) => {
                if (e.target === e.currentTarget) {
                  onEmptyCellClick(staff.id, dateStr);
                }
              }}
            >
              {/* Hour grid lines for visual alignment */}
              {HOUR_TICKS.map((min) => (
                <div
                  key={`grid-${staff.id}-${min}`}
                  aria-hidden
                  className="pointer-events-none absolute top-0 bottom-0 border-l border-slate-100"
                  style={{ left: `${minutesToPercent(min)}%` }}
                />
              ))}
              {positioned.map(({ apt, start, end, lane }) => {
                const left = minutesToPercent(start);
                const right = minutesToPercent(end);
                const widthPct = Math.max(right - left, 0.5);
                const cardStyle: CSSProperties = {
                  left: `${left}%`,
                  width: `${widthPct}%`,
                  top: `${lane * LANE_HEIGHT_PX + 2}px`,
                  height: `${CARD_HEIGHT_PX}px`,
                };
                return (
                  <AppointmentCard
                    key={apt.id}
                    appointment={apt}
                    variant="absolute"
                    isOnSelectedDate={
                      selectedDateStr === apt.scheduled_date
                    }
                    style={cardStyle}
                    onAppointmentClick={onAppointmentClick}
                  />
                );
              })}
              {techAppts.length === 0 && (
                <button
                  type="button"
                  onClick={() => onEmptyCellClick(staff.id, dateStr)}
                  className="absolute inset-2 rounded border border-dashed border-slate-200 text-[11px] text-slate-400 hover:border-teal-300 hover:text-teal-600 hover:bg-teal-50/40"
                  aria-label={`Create appointment for ${staff.name} on ${dateStr}`}
                >
                  +
                </button>
              )}
              {isToday && <NowLine />}
            </div>
          </div>
        );
      })}
    </div>
  );
}
