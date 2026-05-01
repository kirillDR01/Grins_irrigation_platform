/**
 * Pure helpers for the resource-timeline view: time-axis math, lane
 * assignment for overlap-free stacking, and label formatters.
 *
 * No React, no fetch — kept pure so the file is trivially unit-testable
 * and tree-shakable.
 */

import { format, parseISO } from 'date-fns';

/** Visible day window: 6:00 am (360) → 8:00 pm (1200). 840 minutes wide. */
export const DAY_START_MIN = 6 * 60;
export const DAY_END_MIN = 20 * 60;
export const DAY_SPAN_MIN = DAY_END_MIN - DAY_START_MIN;

/** Parse an `HH:MM` or `HH:MM:SS` time string to minutes-since-midnight. */
export function timeToMinutes(t: string): number {
  const [h = '0', m = '0'] = t.split(':');
  return Number(h) * 60 + Number(m);
}

/**
 * Map a minutes-since-midnight value to a percent of the visible day axis.
 * Clamps to [0, 100] so out-of-bounds appointments still render visibly.
 */
export function minutesToPercent(min: number): number {
  const pct = ((min - DAY_START_MIN) / DAY_SPAN_MIN) * 100;
  if (pct < 0) return 0;
  if (pct > 100) return 100;
  return pct;
}

/**
 * Format a time range as `'8:00–9:30'` (en-dash, 24h, no meridiem).
 * The cards are tight; meridiem markers waste space.
 */
export function formatTimeRange(startTime: string, endTime: string): string {
  return `${stripLeadingZero(toHourMinute(startTime))}\u2013${stripLeadingZero(
    toHourMinute(endTime)
  )}`;
}

function toHourMinute(t: string): string {
  const [h = '0', m = '0'] = t.split(':');
  return `${h.padStart(2, '0')}:${m.padStart(2, '0')}`;
}

function stripLeadingZero(hm: string): string {
  return hm.replace(/^0/, '');
}

/**
 * Interval-graph coloring: assigns each item a `lane` (0..N−1) such that
 * no two items with overlapping `[start, end)` intervals share a lane.
 * Greedy by start time with end-time tiebreak — O(n log n).
 *
 * Items are returned sorted by start (then end). Use the returned `lane`
 * to position cards vertically without overlap.
 */
export function assignLanes<T extends { start: number; end: number }>(
  items: T[]
): Array<T & { lane: number }> {
  const sorted = [...items].sort(
    (a, b) => a.start - b.start || a.end - b.end
  );
  const laneEnds: number[] = [];
  const out: Array<T & { lane: number }> = [];
  for (const item of sorted) {
    let lane = -1;
    for (let i = 0; i < laneEnds.length; i++) {
      const end = laneEnds[i];
      if (end !== undefined && end <= item.start) {
        lane = i;
        break;
      }
    }
    if (lane === -1) {
      lane = laneEnds.length;
      laneEnds.push(item.end);
    } else {
      laneEnds[lane] = item.end;
    }
    out.push({ ...item, lane });
  }
  return out;
}

/** Format an ISO date `'2026-04-27'` as `'MON 4/27'` for week-mode headers. */
export function formatDayLabel(isoDate: string): string {
  const d = parseISO(isoDate);
  return `${format(d, 'EEE').toUpperCase()} ${format(d, 'M/d')}`;
}

/**
 * Two-letter initials for an avatar bubble: `'Mike Davis' → 'MD'`,
 * `'Madonna' → 'M'`, `''` or whitespace → `'?'`.
 */
export function getInitials(name: string): string {
  const trimmed = name.trim();
  if (!trimmed) return '?';
  const parts = trimmed.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) {
    return (parts[0] ?? '').charAt(0).toUpperCase() || '?';
  }
  const first = (parts[0] ?? '').charAt(0).toUpperCase();
  const last = (parts[parts.length - 1] ?? '').charAt(0).toUpperCase();
  return `${first}${last}`;
}
