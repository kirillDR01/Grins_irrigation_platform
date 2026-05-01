/**
 * SparklineBar — 16px tall horizontal SVG mini time-map for week-mode cells.
 *
 * Renders one `<rect>` per appointment, x/width as percent of the visible
 * day window (6am–8pm). Tooltip uses a native SVG `<title>` element since
 * `@radix-ui/react-tooltip` is not installed and the ~500ms hover delay
 * is acceptable for at-a-glance scan use.
 */

import { getJobTypeColor } from '../../utils/jobTypeColors';
import type { Appointment } from '../../types';
import {
  formatTimeRange,
  minutesToPercent,
  timeToMinutes,
} from './utils';

export interface SparklineBarProps {
  appointments: Appointment[];
  /** Embedded in `data-testid` for cell-precise selectors. */
  staffId?: string;
  date?: string;
}

export function SparklineBar({
  appointments,
  staffId,
  date,
}: SparklineBarProps) {
  const testId =
    staffId && date ? `sparkline-${staffId}-${date}` : 'sparkline';
  if (appointments.length === 0) {
    return (
      <div
        data-testid={testId}
        className="h-4 bg-slate-50 rounded-sm"
        aria-label="No appointments"
      />
    );
  }
  return (
    <svg
      data-testid={testId}
      viewBox="0 0 100 16"
      preserveAspectRatio="none"
      className="h-4 w-full bg-slate-50 rounded-sm"
      role="img"
      aria-label={`${appointments.length} appointments`}
    >
      {appointments.map((appt) => {
        const startMin = timeToMinutes(appt.time_window_start);
        const endMin = timeToMinutes(appt.time_window_end);
        const x = minutesToPercent(startMin);
        // Floor width at 1% so 30-min jobs are visible at scale.
        const w = Math.max(minutesToPercent(endMin) - x, 1);
        const fill = getJobTypeColor(appt.job_type).fill;
        return (
          <rect
            key={appt.id}
            x={x}
            y={0}
            width={w}
            height={16}
            fill={fill}
          >
            <title>
              {formatTimeRange(
                appt.time_window_start,
                appt.time_window_end
              )}
              {appt.customer_name ? ` — ${appt.customer_name}` : ''}
            </title>
          </rect>
        );
      })}
    </svg>
  );
}
