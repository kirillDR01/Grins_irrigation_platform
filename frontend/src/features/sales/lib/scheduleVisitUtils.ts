// Pure helpers for ScheduleVisitModal. No React, no fetches.
import type { EstimateBlock, Pick, SalesCalendarEvent } from '../types/pipeline';

export const HOUR_START = 6;
export const HOUR_END = 20;
export const SLOT_MIN = 30;
export const SLOT_PX = 22;
export const HEADER_PX = 29;
export const TIMECOL_PX = 56;
export const SLOTS_PER_DAY = ((HOUR_END - HOUR_START) * 60) / SLOT_MIN;

const pad = (n: number) => String(n).padStart(2, '0');

export function minToHHMMSS(m: number): string {
  const h = Math.floor(m / 60);
  const mm = m % 60;
  return `${pad(h)}:${pad(mm)}:00`;
}

export function hhmmssToMin(s: string): number {
  const parts = s.split(':');
  const h = Number(parts[0]);
  const m = Number(parts[1] ?? 0);
  return h * 60 + m;
}

export function startOfWeek(d: Date): Date {
  const nd = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const day = nd.getDay();
  const diff = day === 0 ? -6 : 1 - day; // Monday-start
  nd.setDate(nd.getDate() + diff);
  return nd;
}

export function iso(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function fmtHM(mins: number): string {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  const ap = h >= 12 ? 'PM' : 'AM';
  const h12 = ((h + 11) % 12) + 1;
  return `${h12}:${pad(m)} ${ap}`;
}

export function fmtDur(mins: number): string {
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  if (m === 0) return h === 1 ? '1 hr' : `${h} hr`;
  return `${h}h ${m}m`;
}

export function fmtMonD(d: Date): string {
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function fmtLongDate(isoDate: string): string {
  return new Date(isoDate + 'T12:00').toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  });
}

export function fmtLongDateD(d: Date): string {
  return d.toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  });
}

export function isPastSlot(day: Date, slotMin: number, now: Date): boolean {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (day < today) return true;
  if (iso(day) === iso(now) && slotMin < now.getHours() * 60 + now.getMinutes()) {
    return true;
  }
  return false;
}

export function eventToBlock(
  e: SalesCalendarEvent,
  customerName: string,
  jobSummary: string,
): EstimateBlock {
  return {
    id: e.id,
    date: e.scheduled_date,
    startMin: e.start_time ? hhmmssToMin(e.start_time) : 0,
    endMin: e.end_time ? hhmmssToMin(e.end_time) : 24 * 60,
    customerName,
    jobSummary,
    assignedToUserId: e.assigned_to_user_id,
  };
}

export function detectConflicts(
  pick: Pick | null,
  blocks: EstimateBlock[],
): EstimateBlock[] {
  if (!pick) return [];
  return blocks.filter(
    (b) =>
      b.date === pick.date &&
      !(b.endMin <= pick.start || b.startMin >= pick.end),
  );
}

/**
 * Render a customer's full name as "First L." for the calendar pick block.
 * "Viktor Petrov" → "Viktor P."
 * "Cher" → "Cher"
 * "" / null-ish → "Customer"
 */
export function formatShortName(full: string | null | undefined): string {
  if (!full) return 'Customer';
  const parts = full.trim().split(/\s+/);
  if (parts.length === 0 || !parts[0]) return 'Customer';
  if (parts.length === 1) return parts[0];
  const second = parts[1];
  if (!second) return parts[0];
  return `${parts[0]} ${second[0]}.`;
}
