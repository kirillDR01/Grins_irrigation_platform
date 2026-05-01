/**
 * Shared types for the resource-timeline view (Day / Week / Month modes).
 *
 * Components in this directory consume these types; the orchestrator
 * (`ResourceTimelineView/index.tsx`) owns `ViewMode` state, the mode
 * components consume `TechRow` + `DayColumn` projections, and drag-drop
 * handlers exchange `DragPayload` JSON via `dataTransfer`.
 */

import type { Staff } from '@/features/staff/types';
import type { Appointment } from '../../types';

export type ViewMode = 'day' | 'week' | 'month';

export interface TechRow {
  staff: Staff;
  appointments: Appointment[];
  utilizationPct: number;
}

export interface DayColumn {
  /** ISO date string YYYY-MM-DD. */
  date: string;
  /** Display label like 'MON 4/27'. */
  label: string;
  jobCount: number;
  /** null while the per-day capacity query is loading. */
  capacityPct: number | null;
}

export interface PositionedAppointment extends Appointment {
  /** Lane index assigned by `assignLanes` for overlap-free stacking. */
  lane: number;
  /** Cached minutes-since-midnight for `time_window_start`. */
  startMin: number;
  /** Cached minutes-since-midnight for `time_window_end`. */
  endMin: number;
}

export interface DragPayload {
  appointmentId: string;
  originStaffId: string;
  /** YYYY-MM-DD. */
  originDate: string;
  /** HH:MM:SS. */
  originStartTime: string;
  /** HH:MM:SS. */
  originEndTime: string;
}
