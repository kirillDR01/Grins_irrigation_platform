/**
 * DayHeader — clickable column header for week mode.
 *
 * The label + count is wrapped in a `<button>` for keyboard accessibility
 * (Enter activates the drill-in). The day-confirmations action button is
 * a sibling, not a child, since button-in-button is invalid HTML.
 */

import { ChevronDown } from 'lucide-react';
import { SendDayConfirmationsButton } from '../SendDayConfirmationsButton';
import { formatDayLabel } from './utils';
import type { Appointment } from '../../types';

export interface DayHeaderProps {
  /** ISO date `YYYY-MM-DD`. */
  date: string;
  jobCount: number;
  isToday: boolean;
  draftAppointments: Appointment[];
  onDrillIn: (date: string) => void;
}

export function DayHeader({
  date,
  jobCount,
  isToday,
  draftAppointments,
  onDrillIn,
}: DayHeaderProps) {
  const labelColor = isToday
    ? 'text-teal-600'
    : 'text-slate-500';
  const todayUnderline = isToday ? 'underline underline-offset-4' : '';

  return (
    <div
      data-testid={`day-header-${date}`}
      className="flex items-center justify-center gap-1 p-2 border-b border-slate-100 group"
    >
      <button
        type="button"
        onClick={() => onDrillIn(date)}
        className={[
          'flex flex-col items-center gap-0.5 cursor-pointer rounded px-1 py-0.5',
          'hover:bg-slate-50 hover:underline underline-offset-4',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2',
          labelColor,
          todayUnderline,
        ].join(' ')}
        aria-label={`View ${formatDayLabel(date)} day mode`}
      >
        <span className="text-xs font-semibold uppercase tracking-wider flex items-center gap-1">
          {formatDayLabel(date)}
          <ChevronDown
            className="size-3 opacity-0 group-hover:opacity-100 transition-opacity"
            aria-hidden
          />
        </span>
        <span className="text-[11px] text-slate-500 normal-case">
          {jobCount} {jobCount === 1 ? 'job' : 'jobs'}
        </span>
      </button>
      {draftAppointments.length > 0 && (
        <SendDayConfirmationsButton
          date={date}
          draftAppointments={draftAppointments}
        />
      )}
    </div>
  );
}
