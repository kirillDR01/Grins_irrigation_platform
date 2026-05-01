/**
 * ResourceTimelineView — orchestrator for the day/week/month resource grid.
 *
 * Owns: ViewMode + currentDate state, prev/next/today nav, and the
 * orchestration handlers for empty-cell click → create dialog and
 * day-header click → drill into Day mode.
 */

import { useCallback, useState } from 'react';
import {
  addDays,
  addMonths,
  endOfMonth,
  format,
  parseISO,
  startOfMonth,
  startOfWeek,
} from 'date-fns';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DayMode } from './DayMode';
import { MonthMode } from './MonthMode';
import { ViewModeToggle } from './ViewModeToggle';
import { WeekMode } from './WeekMode';
import type { ViewMode } from './types';

export interface ResourceTimelineViewProps {
  /** Called when the user clicks an empty `[tech × day]` cell (week mode).
   *  The optional staffId pre-fills the create-appointment form's
   *  `initialStaffId`. */
  onDateClick?: (staffId: string | null, date: Date) => void;
  onEventClick?: (appointmentId: string) => void;
  onWeekChange?: (weekStart: Date) => void;
  selectedDate?: Date | null;
  /** Reserved for inline customer panel (CalendarView legacy). The
   *  resource-timeline view routes the appointment-card click through
   *  `onEventClick` instead, so this prop is currently unused. */
  onCustomerClick?: (appointmentId: string) => void;
}

export function ResourceTimelineView({
  onDateClick,
  onEventClick,
  onWeekChange,
  selectedDate,
}: ResourceTimelineViewProps) {
  const [mode, setMode] = useState<ViewMode>('week');
  const [currentDate, setCurrentDate] = useState<Date>(() => new Date());

  const weekStart = startOfWeek(currentDate, { weekStartsOn: 1 });

  const handleWeekModeNav = useCallback(
    (newDate: Date) => {
      setCurrentDate(newDate);
      const newWeekStart = startOfWeek(newDate, { weekStartsOn: 1 });
      onWeekChange?.(newWeekStart);
    },
    [onWeekChange]
  );

  const handlePrev = () => {
    if (mode === 'day') {
      handleWeekModeNav(addDays(currentDate, -1));
    } else if (mode === 'week') {
      handleWeekModeNav(addDays(weekStart, -7));
    } else {
      handleWeekModeNav(addMonths(currentDate, -1));
    }
  };
  const handleNext = () => {
    if (mode === 'day') {
      handleWeekModeNav(addDays(currentDate, 1));
    } else if (mode === 'week') {
      handleWeekModeNav(addDays(weekStart, 7));
    } else {
      handleWeekModeNav(addMonths(currentDate, 1));
    }
  };
  const handleToday = () => {
    handleWeekModeNav(new Date());
  };

  const handleDayHeaderClick = useCallback(
    (isoDate: string) => {
      const d = parseISO(isoDate);
      setCurrentDate(d);
      setMode('day');
    },
    []
  );

  const handleEmptyCellClick = useCallback(
    (staffId: string, isoDate: string) => {
      onDateClick?.(staffId, parseISO(isoDate));
    },
    [onDateClick]
  );

  const handleAppointmentClick = useCallback(
    (id: string) => {
      onEventClick?.(id);
    },
    [onEventClick]
  );

  const rangeLabel = (() => {
    if (mode === 'day') return format(currentDate, 'MMMM d, yyyy');
    if (mode === 'week') {
      const weekEnd = addDays(weekStart, 6);
      return `${format(weekStart, 'MMM d')} – ${format(weekEnd, 'MMM d, yyyy')}`;
    }
    const monthStart = startOfMonth(currentDate);
    const monthEnd = endOfMonth(currentDate);
    return `${format(monthStart, 'MMM d')} – ${format(monthEnd, 'MMM d, yyyy')}`;
  })();

  return (
    <div
      data-testid="schedule-resource-timeline"
      className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden"
    >
      <div className="flex items-center justify-between gap-2 border-b border-slate-100 px-3 py-2 flex-wrap">
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            data-testid="nav-prev-btn"
            onClick={handlePrev}
            aria-label="Previous"
          >
            <ChevronLeft className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            data-testid="nav-next-btn"
            onClick={handleNext}
            aria-label="Next"
          >
            <ChevronRight className="size-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            data-testid="nav-today-btn"
            onClick={handleToday}
          >
            Today
          </Button>
          <span className="ml-2 text-sm font-semibold text-slate-700">
            {rangeLabel}
          </span>
        </div>
        <ViewModeToggle mode={mode} onModeChange={setMode} />
      </div>

      {mode === 'week' && (
        <WeekMode
          weekStart={weekStart}
          selectedDate={selectedDate ?? null}
          onAppointmentClick={handleAppointmentClick}
          onEmptyCellClick={handleEmptyCellClick}
          onDayHeaderClick={handleDayHeaderClick}
        />
      )}
      {mode === 'day' && (
        <DayMode
          date={currentDate}
          selectedDate={selectedDate ?? null}
          onAppointmentClick={handleAppointmentClick}
          onEmptyCellClick={handleEmptyCellClick}
        />
      )}
      {mode === 'month' && (
        <MonthMode
          date={currentDate}
          onDayHeaderClick={handleDayHeaderClick}
        />
      )}
    </div>
  );
}
